// Session machines for Syntra v1 Go servers: transport-agnostic Client
// (initiator) and Host (responder) built on the validation and codec
// primitives in syntra.go.
//
// A Transport carries exactly one serialized Frame per Send/Recv call in
// each direction. This binding does not dial TCP/TLS or WebSocket: the
// host application owns the socket and plugs it in here (length-prefix,
// binary-message, and close-code bindings per specifications/transports).
// LoopbackPair provides an in-memory Transport for tests and embedding.
//
// Both Client and Host delegate state (handshake machine, correlation,
// timers) to a core selected at build time: the Rust-backed CGO core
// with -tags syntranative (native.go) or the pure-Go core otherwise
// (native_purego.go). Behavior is identical; NativeAvailable reports
// which core is linked.
//
// Context deadlines and cancellation: every blocking call honors ctx.
// Call derives the wire timeout_ms budget as the minimum of the
// requested budget and the time remaining on ctx; ctx cancellation sends
// a best-effort cancel frame and reports CANCELLED (context.Canceled) or
// DEADLINE_EXCEEDED (context.DeadlineExceeded / budget expiry) without
// waiting for the late terminal result, which the pump still consumes to
// keep correlation exact.
package syntra

import (
	"context"
	"errors"
	"fmt"
	"io"
	"sync"
	"sync/atomic"
	"time"

	syntrav1 "github.com/tinklehq/syntra/bindings/go/gen/syntra/v1"
)

// Transport carries serialized Syntra Frames. Each Send transmits exactly
// one Frame toward the peer; each Recv returns exactly one inbound Frame.
// Implementations MUST preserve frame boundaries and MUST NOT batch
// multiple Frames into one Send payload. The session layer validates
// sizes and contents; transports MUST still bound allocation on receive.
type Transport interface {
	// Send transmits one serialized Frame. It MUST copy frame if it
	// retains it.
	Send(ctx context.Context, frame []byte) error
	// Recv returns the next inbound serialized Frame. It returns an
	// error when the transport is closed and drained or ctx ends.
	Recv(ctx context.Context) ([]byte, error)
	// Close releases the transport. It is idempotent.
	Close() error
}

// loopback is an in-memory Transport. Frames cross by value (Send copies)
// so callers can reuse buffers.
type loopback struct {
	mu     sync.Mutex
	inbox  chan []byte
	closed bool
	peer   *loopback
}

const loopbackBuffer = 64

// LoopbackPair returns two connected in-memory Transports: frames sent
// on a arrive on b and vice versa. It is the standard harness for
// lifecycle tests and for embedding a session without a socket.
func LoopbackPair() (a, b Transport) {
	x := &loopback{inbox: make(chan []byte, loopbackBuffer)}
	y := &loopback{inbox: make(chan []byte, loopbackBuffer)}
	x.peer = y
	y.peer = x
	return x, y
}

// Send transmits one frame toward the peer. A closed transport reports
// Unavailable; an oversize frame is rejected before allocation.
func (l *loopback) Send(ctx context.Context, frame []byte) error {
	if err := ValidateFrameSize(len(frame)); err != nil {
		return err
	}
	cp := make([]byte, len(frame))
	copy(cp, frame)
	l.mu.Lock()
	peer := l.peer
	l.mu.Unlock()
	_ = l
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}
	peer.mu.Lock()
	closed := peer.closed
	peer.mu.Unlock()
	if closed {
		return NewRpcError(ErrorCodeUnavailable, "syntra: loopback peer closed")
	}
	select {
	case <-ctx.Done():
		return ctx.Err()
	case peer.inbox <- cp:
		return nil
	default:
		return NewRpcError(ErrorCodeResourceExhausted, "syntra: loopback peer inbox full")
	}
}

// Recv returns the next inbound frame, draining buffered frames after
// Close before reporting Unavailable.
func (l *loopback) Recv(ctx context.Context) ([]byte, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case f, ok := <-l.inbox:
		if !ok {
			return nil, NewRpcError(ErrorCodeUnavailable, "syntra: loopback closed")
		}
		if err := ValidateFrameSize(len(f)); err != nil {
			return nil, err
		}
		return f, nil
	default:
	}
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case f, ok := <-l.inbox:
		if !ok {
			return nil, NewRpcError(ErrorCodeUnavailable, "syntra: loopback closed")
		}
		if err := ValidateFrameSize(len(f)); err != nil {
			return nil, err
		}
		return f, nil
	}
}

// Close drains and releases the transport. It is idempotent.
func (l *loopback) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.closed {
		return nil
	}
	l.closed = true
	close(l.inbox)
	if l.peer != nil {
		l.peer.mu.Lock()
		if !l.peer.closed {
			l.peer.closed = true
			close(l.peer.inbox)
		}
		l.peer.mu.Unlock()
	}
	return nil
}

// StaticPolicy returns a CredentialPolicy that accepts any credential and
// binds principal. It is intended for tests, examples, and
// anonymous-intent deployments; production hosts MUST verify credentials
// against their identity system. When allowEmpty is false, empty
// credentials are rejected as Unauthenticated.
func StaticPolicy(principal string, allowEmpty bool) CredentialPolicy {
	return func(ctx context.Context, credential []byte) (string, error) {
		if err := ctx.Err(); err != nil {
			return "", NewRpcError(ErrorCodeUnavailable, "syntra: policy context ended")
		}
		if principal == "" {
			return "", NewRpcError(ErrorCodeInternal, "syntra: policy principal misconfigured")
		}
		if len(credential) == 0 && !allowEmpty {
			return "", NewRpcError(ErrorCodeUnauthenticated, "syntra: credential required")
		}
		return principal, nil
	}
}

// HandlerFunc implements one application method for a Host. It receives
// the validated RpcRequest with ctx bounded by the effective call budget
// (cancellation propagates client cancel frames and conn teardown). It
// returns either a valid *RpcResult or an error: a *RpcError becomes the
// wire error outcome; any other error becomes a generic INTERNAL outcome
// so handler internals never leak to the peer (SNTR-ERR-003). Returning
// (nil, nil) is a handler bug and is reported as INTERNAL.
type HandlerFunc func(ctx context.Context, req *RpcRequest) (*RpcResult, error)

// clientCore owns initiator-side session state: handshake progress,
// correlation, timers, and notification queue. Implementations are the
// Rust-backed CGO core (native.go) or the pure-Go core
// (native_purego.go). All methods except close are invalid after close
// reports, and report FailedPrecondition once closed.
type clientCore interface {
	// helloFrame returns the hello frame to transmit. It fails closed on
	// invalid config (empty version range, oversize credential).
	helloFrame() ([]byte, error)
	// activate validates the ServerReady frame, pins the negotiated
	// version, and moves the session to ACTIVE.
	activate(frame []byte) (*ServerReady, error)
	// version returns the negotiated version, or 0 before activate.
	version() uint32
	// onFrame validates one inbound frame and stores its terminal
	// effects. It returns the request IDs whose outcomes became terminal
	// (to deliver) and the number of queued notifications. A fatal
	// protocol violation is returned as *RpcError and the session MUST
	// be torn down by the caller.
	onFrame(frame []byte) (terminal []uint64, notifications int, fatal *RpcError)
	// beginCall validates and registers an outbound call and returns the
	// request frame to transmit.
	beginCall(requestID uint64, method string, payload []byte, timeoutMs uint32) (reqFrame []byte, err error)
	// cancelCall marks an outstanding call cancelled and returns the
	// cancel frame to transmit, or nil when the id is unknown (ignored
	// per SNTR-RPC-005, no error, no frame).
	cancelCall(requestID uint64) (cancelFrame []byte)
	// takeOutcome consumes the terminal outcome for id. ok is false when
	// the call is not terminal yet (or unknown).
	takeOutcome(requestID uint64) (result *RpcResult, ok bool)
	// pollNotification consumes one queued notification, or ok == false.
	pollNotification() (*Notification, bool)
	// reapExpired removes calls whose deadlines passed, stores a
	// DEADLINE_EXCEEDED outcome for each, and returns their ids for
	// delivery. Completion wins: ids with a stored outcome are skipped.
	reapExpired(now time.Time) (expired []uint64)
	// close deterministically releases the core. Second close reports
	// FailedPrecondition.
	close() error
}

// hostCore owns responder-side per-connection state: handshake progress,
// pending validated requests, outstanding call deadlines, cancellation
// marks, and the outbound queue. Handler dispatch itself lives in Go
// (Host.Serve); the core never interprets application payloads.
type hostCore interface {
	// acceptHello validates the ClientHello frame, negotiates the
	// highest overlap against the configured range, and returns the
	// selected version. State advances to NEGOTIATING.
	acceptHello(frame []byte) (version uint32, err error)
	// authComplete binds principal, advances to ACTIVE, and returns the
	// ServerReady frame to transmit.
	authComplete(principal string) (readyFrame []byte, err error)
	// onFrame validates one inbound frame. Immediate response frames
	// (ready is produced by authComplete; ACTIVE-phase validation
	// failures produce error results here) are returned for transmit.
	// Requests that pass validation are queued for takePending.
	// cancelIDs names outstanding calls the peer cancelled. A fatal
	// protocol violation (handshake-phase failure, empty body, version
	// mismatch) is returned and the caller MUST close the connection.
	onFrame(frame []byte) (responses [][]byte, cancelIDs []uint64, fatal *RpcError)
	// takePending dequeues one validated request for dispatch.
	takePending() (requestID uint64, req *RpcRequest, ok bool)
	// isCancelled reports whether id was cancelled by the peer.
	isCancelled(requestID uint64) bool
	// answer validates and enqueues the terminal result frame, returning
	// it for transmit. When the call expired first, expired is true (a
	// DEADLINE_EXCEEDED result was auto-enqueued instead) and resp is nil.
	answer(requestID uint64, result *RpcResult) (resp []byte, expired bool, err error)
	// notify validates and enqueues a broadcast notification.
	notify(payload []byte) error
	// nextOutbound dequeues one queued frame (results, auto-deadline
	// results, notifications), or ok == false when empty.
	nextOutbound() (frame []byte, ok bool)
	// reapExpired removes calls whose deadlines passed, auto-enqueues a
	// DEADLINE_EXCEEDED result for each, and returns their ids so the
	// caller can abandon the handlers.
	reapExpired(now time.Time) (expired []uint64)
	// close deterministically releases the core. Second close reports
	// FailedPrecondition.
	close() error
}

// activatedReady is the validated outcome of a client handshake.
type activatedReady struct {
	ready        *ServerReady
	frameVersion uint32
}

// activateFrame validates one inbound ServerReady frame against the
// proposed range and returns the selected version. Shared by both cores
// so handshake acceptance is identical with and without native.
func activateFrame(frame []byte, minVersion, maxVersion uint32) (*activatedReady, error) {
	f, err := UnmarshalFrame(frame)
	if err != nil {
		return nil, err
	}
	if BodyKindOf(f) != BodyKindReady {
		return nil, NewRpcError(ErrorCodeFailedPrecondition, "syntra: handshake expects ready")
	}
	if f.GetRequestId() != 0 {
		return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: ready frame must carry request_id 0")
	}
	v := f.GetVersion()
	if v < minVersion || v > maxVersion {
		return nil, NewRpcError(ErrorCodeUnimplemented, "syntra: server selected version outside proposed range")
	}
	if err := ValidateReady(f.GetReady()); err != nil {
		return nil, err
	}
	return &activatedReady{ready: f.GetReady(), frameVersion: v}, nil
}

// decodeResultFrame validates owned result-frame bytes from a core into
// the terminal RpcResult. Unknown wire error codes normalize to UNKNOWN
// (SNTR-ERR-005); a missing outcome is INVALID_ARGUMENT, never success.
func decodeResultFrame(raw []byte) (*RpcResult, error) {
	f, err := UnmarshalFrame(raw)
	if err != nil {
		return nil, err
	}
	if BodyKindOf(f) != BodyKindResult {
		return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: expected result frame")
	}
	res := f.GetResult()
	if err := ValidateResult(res); err != nil {
		return nil, err
	}
	return res, nil
}

// decodeNotificationFrame validates owned notification-frame bytes from
// a core into the event payload.
func decodeNotificationFrame(raw []byte) (*Notification, error) {
	f, err := UnmarshalFrame(raw)
	if err != nil {
		return nil, err
	}
	if BodyKindOf(f) != BodyKindNotification {
		return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: expected notification frame")
	}
	if f.GetNotification() == nil {
		return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: nil notification")
	}
	return f.GetNotification(), nil
}

// resolvedClientConfig is a ClientConfig with defaults applied.
type resolvedClientConfig struct {
	minVersion   uint32
	maxVersion   uint32
	credential   []byte
	timeout      time.Duration
	maxPending   int
	notifyBuffer int
}

// ClientConfig configures a Client session.
type ClientConfig struct {
	// MinVersion/MaxVersion bound the proposed handshake range. Zero
	// selects the binding singleton (v1). Min must not exceed Max.
	MinVersion uint32
	// MaxVersion is the proposed maximum; the hello frame carries it.
	MaxVersion uint32
	// Credential is the opaque hello credential. Empty is an attempt
	// subject to host policy, not a parse error; oversize fails fast.
	Credential []byte
	// DefaultTimeout applies when a call passes timeoutMs zero. Zero
	// selects DefaultRPCTimeout. Negative fails fast.
	DefaultTimeout time.Duration
	// MaxConcurrent caps outstanding calls. Zero selects
	// MaxConcurrentRPCs. Excess calls fail fast with ResourceExhausted.
	MaxConcurrent int
	// NotifyBuffer sizes the notification queue. Zero selects 16.
	// Overflow drops the newest notification and counts it (see
	// DroppedNotifications).
	NotifyBuffer int
}

func resolveClientConfig(cfg ClientConfig) (resolvedClientConfig, error) {
	out := resolvedClientConfig{
		minVersion:   cfg.MinVersion,
		maxVersion:   cfg.MaxVersion,
		credential:   cfg.Credential,
		timeout:      cfg.DefaultTimeout,
		maxPending:   cfg.MaxConcurrent,
		notifyBuffer: cfg.NotifyBuffer,
	}
	if out.minVersion == 0 {
		out.minVersion = MinSupportedVersion
	}
	if out.maxVersion == 0 {
		out.maxVersion = MaxSupportedVersion
	}
	if out.minVersion > out.maxVersion {
		return resolvedClientConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: client min_version exceeds max_version")
	}
	if err := ValidateCredentialSize(out.credential); err != nil {
		return resolvedClientConfig{}, err
	}
	if out.timeout == 0 {
		out.timeout = DefaultRPCTimeout
	}
	if out.timeout <= 0 {
		return resolvedClientConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: client default timeout must be positive")
	}
	if out.maxPending == 0 {
		out.maxPending = MaxConcurrentRPCs
	}
	if out.maxPending < 1 {
		return resolvedClientConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: client max concurrent must be positive")
	}
	if out.notifyBuffer == 0 {
		out.notifyBuffer = 16
	}
	if out.notifyBuffer < 1 {
		return resolvedClientConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: notify buffer must be positive")
	}
	return out, nil
}

// Client is an initiator-side Syntra session. The zero value is invalid;
// construct with OpenClient. A Client is safe for concurrent Call and
// notification subscription; one Run pump owns the Transport.
type Client struct {
	core   clientCore
	cfg    resolvedClientConfig
	nextID atomic.Uint64

	mu        sync.Mutex
	cond      *sync.Cond // guards handshake completion for early Call
	active    bool
	closed    bool
	done      chan struct{}
	waiters   map[uint64]chan *RpcResult
	notifyCh  chan *Notification
	dropped   atomic.Uint64
	transport Transport
}

// OpenClient creates an initiator session. It validates the config and
// opens the linked core (native or pure-Go) but performs no I/O; call
// Run to handshake and pump a Transport.
func OpenClient(cfg ClientConfig) (*Client, error) {
	rcfg, err := resolveClientConfig(cfg)
	if err != nil {
		return nil, err
	}
	core, err := newClientCore(rcfg)
	if err != nil {
		return nil, err
	}
	c := &Client{
		core:     core,
		cfg:      rcfg,
		done:     make(chan struct{}),
		waiters:  make(map[uint64]chan *RpcResult),
		notifyCh: make(chan *Notification, rcfg.notifyBuffer),
	}
	c.cond = sync.NewCond(&c.mu)
	return c, nil
}

// Notifications returns the notification stream. The channel is closed
// when the session closes. Overflow drops the newest notification and
// counts it; see DroppedNotifications. Receive promptly or size
// NotifyBuffer for bursts.
func (c *Client) Notifications() <-chan *Notification {
	return c.notifyCh
}

// DroppedNotifications reports notifications discarded under overflow.
func (c *Client) DroppedNotifications() uint64 {
	if c == nil {
		return 0
	}
	return c.dropped.Load()
}

// failWaiters completes outstanding calls with err. Callers MUST hold c.mu.
func (c *Client) failWaitersLocked(code ErrorCode, msg string) {
	res := NewWireErrorResult(code, msg)
	for id, w := range c.waiters {
		delete(c.waiters, id)
		select {
		case w <- res:
		default:
		}
	}
}

// handshake performs the hello/ready exchange on t.
func (c *Client) handshake(ctx context.Context, t Transport) (*ServerReady, error) {
	hello, err := c.core.helloFrame()
	if err != nil {
		return nil, err
	}
	if err := t.Send(ctx, hello); err != nil {
		return nil, err
	}
	raw, err := t.Recv(ctx)
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return nil, err
		}
		return nil, NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: handshake recv: %v", err))
	}
	ready, err := c.core.activate(raw)
	if err != nil {
		return nil, err
	}
	c.mu.Lock()
	c.active = true
	c.transport = t
	c.cond.Broadcast()
	c.mu.Unlock()
	return ready, nil
}

// Run handshakes on t, then pumps frames until ctx ends, the transport
// fails, a fatal protocol violation arrives, or Close is called. It
// returns nil only on a clean shutdown (Close or ctx end with no
// outstanding violation); transport and protocol failures are returned.
// Call Run once per Client in its own goroutine; concurrent Calls share
// the pump.
func (c *Client) Run(ctx context.Context, t Transport) error {
	if c == nil {
		return NewRpcError(ErrorCodeInternal, "syntra: nil client")
	}
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: client closed")
	}
	if c.transport != nil {
		c.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: client already running")
	}
	c.mu.Unlock()

	if _, err := c.handshake(ctx, t); err != nil {
		_ = c.core.close()
		c.mu.Lock()
		c.closed = true
		c.cond.Broadcast()
		close(c.done)
		c.mu.Unlock()
		return err
	}
	err := c.pump(ctx, t)
	_ = c.core.close()
	c.mu.Lock()
	// Close may have run concurrently (it owns the same teardown); only
	// the first party closes the channels.
	if !c.closed {
		c.closed = true
		c.cond.Broadcast()
		c.failWaitersLocked(ErrorCodeUnavailable, "syntra: client closed")
		close(c.done)
		close(c.notifyCh)
	}
	c.mu.Unlock()
	if err == nil {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		return nil
	}
	return err
}

// recvResult is one transport read: exactly one serialized frame or the
// terminal read error.
type recvResult struct {
	raw []byte
	err error
}

// pumpTick bounds deadline granularity for calls whose budget expires
// while no frames arrive. Reaping is idempotent and cheap on both cores.
const pumpTick = 10 * time.Millisecond

// pump routes inbound frames to call waiters and the notification
// stream, and reaps expired calls on a tick so budgets fire even when
// the peer goes silent.
func (c *Client) pump(ctx context.Context, t Transport) error {
	pumpCtx, pumpStop := context.WithCancel(context.Background())
	defer pumpStop()
	go func() {
		select {
		case <-ctx.Done():
			pumpStop()
		case <-c.done:
			pumpStop()
		}
	}()
	recvCh := make(chan recvResult, 1)
	go func() {
		for {
			raw, err := t.Recv(pumpCtx)
			select {
			case recvCh <- recvResult{raw: raw, err: err}:
			case <-pumpCtx.Done():
				return
			}
			if err != nil {
				return
			}
		}
	}()
	ticker := time.NewTicker(pumpTick)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-c.done:
			return nil
		case r := <-recvCh:
			if r.err != nil {
				if errors.Is(r.err, context.Canceled) || errors.Is(r.err, context.DeadlineExceeded) {
					return nil
				}
				var rerr *RpcError
				if errors.As(r.err, &rerr) {
					c.failWaiters(rerr.Code, rerr.Message)
					return r.err
				}
				if errors.Is(r.err, io.EOF) {
					c.failWaiters(ErrorCodeUnavailable, "syntra: transport closed")
					return NewRpcError(ErrorCodeUnavailable, "syntra: transport closed")
				}
				c.failWaiters(ErrorCodeUnavailable, "syntra: transport recv failed")
				return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: transport recv: %v", r.err))
			}
			terminal, n, fatal := c.core.onFrame(r.raw)
			if fatal != nil {
				c.failWaiters(fatal.Code, fatal.Message)
				return fatal
			}
			for i := 0; i < n; i++ {
				if ntf, ok := c.core.pollNotification(); ok {
					select {
					case c.notifyCh <- ntf:
					default:
						c.dropped.Add(1)
					}
				}
			}
			for _, id := range terminal {
				if res, ok := c.core.takeOutcome(id); ok {
					c.deliver(id, res)
				}
			}
			c.reap(time.Now())
		case <-ticker.C:
			c.reap(time.Now())
		}
	}
}

// reap expires overdue calls and delivers their DEADLINE_EXCEEDED
// outcomes to waiters (or discards them when the waiter already left;
// the core already consumed the outcome either way).
func (c *Client) reap(now time.Time) {
	for _, id := range c.core.reapExpired(now) {
		if res, ok := c.core.takeOutcome(id); ok {
			c.deliver(id, res)
		}
	}
}

// failWaiters completes outstanding calls with a synthesized error.
func (c *Client) failWaiters(code ErrorCode, msg string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.failWaitersLocked(code, msg)
}

// deliver routes one terminal outcome to its waiter, discarding it when
// the waiter already left (cancelled or timed-out locally). The core
// already consumed the outcome, so correlation stays exact either way.
func (c *Client) deliver(id uint64, res *RpcResult) {
	c.mu.Lock()
	w, ok := c.waiters[id]
	if ok {
		delete(c.waiters, id)
	}
	c.mu.Unlock()
	if !ok {
		return
	}
	select {
	case w <- res:
	default:
	}
}

// Call invokes method with payload and waits for exactly one terminal
// result. timeoutMs zero selects the configured default; larger than
// MaxRPCTimeoutMs fails fast. The effective budget is the minimum of the
// requested budget and ctx's remaining time. On ctx end the binding sends
// a best-effort cancel and reports CANCELLED (ctx canceled) or
// DEADLINE_EXCEEDED (ctx deadline / budget expiry). A successful outcome
// returns the opaque payload bytes; an error outcome is returned as
// *RpcError (branch on Code, never on message text).
func (c *Client) Call(ctx context.Context, method string, payload []byte, timeoutMs uint32) ([]byte, error) {
	if c == nil {
		return nil, NewRpcError(ErrorCodeInternal, "syntra: nil client")
	}
	if err := ctx.Err(); err != nil {
		return nil, mapContextErr(err)
	}
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil, NewRpcError(ErrorCodeFailedPrecondition, "syntra: client closed")
	}
	for !c.active {
		c.cond.Wait()
		if c.closed {
			c.mu.Unlock()
			return nil, NewRpcError(ErrorCodeFailedPrecondition, "syntra: client closed")
		}
	}
	t := c.transport
	c.mu.Unlock()

	budget := c.cfg.timeout
	if timeoutMs > 0 {
		budget = time.Duration(timeoutMs) * time.Millisecond
	}
	if deadline, ok := ctx.Deadline(); ok {
		if remaining := time.Until(deadline); remaining <= 0 {
			return nil, NewRpcError(ErrorCodeDeadlineExceeded, "syntra: context deadline already exceeded")
		} else if remaining < budget {
			budget = remaining
		}
	}
	if err := ValidatePayloadSize(len(payload)); err != nil {
		return nil, err
	}
	id := c.nextID.Add(1)
	wireTimeout := uint32(budget / time.Millisecond)
	if wireTimeout == 0 {
		wireTimeout = 1
	}
	reqFrame, err := c.core.beginCall(id, method, payload, wireTimeout)
	if err != nil {
		return nil, err
	}
	w := make(chan *RpcResult, 1)
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return nil, NewRpcError(ErrorCodeFailedPrecondition, "syntra: client closed")
	}
	c.waiters[id] = w
	c.mu.Unlock()

	removeWaiter := func() {
		c.mu.Lock()
		if cur, ok := c.waiters[id]; ok && cur == w {
			delete(c.waiters, id)
		}
		c.mu.Unlock()
	}

	if err := t.Send(ctx, reqFrame); err != nil {
		removeWaiter()
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			c.cancelBestEffort(id)
			return nil, mapContextErr(ctx.Err())
		}
		return nil, NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: send request: %v", err))
	}
	select {
	case res := <-w:
		return finishCall(res)
	case <-ctx.Done():
		removeWaiter()
		c.cancelBestEffort(id)
		if ctx.Err() != nil {
			return nil, mapContextErr(ctx.Err())
		}
		return nil, NewRpcError(ErrorCodeCancelled, "syntra: call cancelled")
	case <-c.done:
		removeWaiter()
		return nil, NewRpcError(ErrorCodeUnavailable, "syntra: client closed")
	}
}

// cancelBestEffort marks the call cancelled and transmits the cancel
// frame, ignoring transport errors: cancellation is advisory
// (SNTR-RPC-005) and the late terminal result still converges the
// correlation table via the pump.
func (c *Client) cancelBestEffort(id uint64) {
	frame := c.core.cancelCall(id)
	if len(frame) == 0 {
		return
	}
	c.mu.Lock()
	t := c.transport
	c.mu.Unlock()
	if t == nil {
		return
	}
	ctx, stop := context.WithTimeout(context.Background(), time.Second)
	defer stop()
	_ = t.Send(ctx, frame)
}

// finishCall converts a terminal wire outcome to the Call contract.
func finishCall(res *RpcResult) ([]byte, error) {
	if res == nil {
		return nil, NewRpcError(ErrorCodeInternal, "syntra: nil terminal outcome")
	}
	switch outcome := res.GetOutcome().(type) {
	case *syntrav1.RpcResult_Payload:
		out := make([]byte, len(outcome.Payload))
		copy(out, outcome.Payload)
		return out, nil
	case *syntrav1.RpcResult_Error:
		if outcome.Error == nil {
			return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: result missing outcome")
		}
		return nil, RpcErrorFromWire(outcome.Error)
	default:
		return nil, NewRpcError(ErrorCodeInvalidArgument, "syntra: result missing outcome")
	}
}

// mapContextErr converts a context error to the Syntra code that owns the
// outcome: cancellation is CANCELLED, expiry is DEADLINE_EXCEEDED.
func mapContextErr(err error) *RpcError {
	if errors.Is(err, context.DeadlineExceeded) {
		return NewRpcError(ErrorCodeDeadlineExceeded, "syntra: deadline exceeded")
	}
	return NewRpcError(ErrorCodeCancelled, "syntra: call cancelled")
}

// Close deterministically releases the session: in-flight calls complete
// with UNAVAILABLE, the notification stream closes, and the core is
// destroyed exactly once. A second Close reports FailedPrecondition so
// double-close bugs surface instead of passing. Close does not close the
// Transport; its owner retains that.
func (c *Client) Close() error {
	if c == nil {
		return NewRpcError(ErrorCodeInternal, "syntra: nil client")
	}
	c.mu.Lock()
	if c.closed {
		c.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: client already closed")
	}
	c.closed = true
	c.cond.Broadcast()
	c.failWaitersLocked(ErrorCodeUnavailable, "syntra: client closed")
	close(c.done)
	close(c.notifyCh)
	core := c.core
	c.mu.Unlock()
	if err := core.close(); err != nil {
		return err
	}
	return nil
}

// resolvedHostConfig is a HostConfig with defaults applied.
type resolvedHostConfig struct {
	minVersion uint32
	maxVersion uint32
	policy     CredentialPolicy
	handler    HandlerFunc
	timeout    time.Duration
	maxPending int
}

// HostConfig configures a Host session factory. Each Serve call opens one
// independent per-connection core from this config.
type HostConfig struct {
	// MinVersion/MaxVersion bound the accepted handshake range. Zero
	// selects the binding singleton (v1).
	MinVersion uint32
	// MaxVersion is the highest version the host emits.
	MaxVersion uint32
	// Policy verifies hello credentials and returns the principal to
	// bind. Nil denies every handshake as Unauthenticated.
	Policy CredentialPolicy
	// Handler dispatches validated requests. Nil answers every request
	// UNIMPLEMENTED (no method is known).
	Handler HandlerFunc
	// DefaultTimeout applies when a request passes timeoutMs zero. Zero
	// selects DefaultRPCTimeout. Negative fails fast.
	DefaultTimeout time.Duration
	// MaxConcurrent caps outstanding calls per connection. Zero selects
	// MaxConcurrentRPCs. Excess calls fail with ResourceExhausted while
	// the connection stays usable.
	MaxConcurrent int
}

func resolveHostConfig(cfg HostConfig) (resolvedHostConfig, error) {
	out := resolvedHostConfig{
		minVersion: cfg.MinVersion,
		maxVersion: cfg.MaxVersion,
		policy:     cfg.Policy,
		handler:    cfg.Handler,
		timeout:    cfg.DefaultTimeout,
		maxPending: cfg.MaxConcurrent,
	}
	if out.minVersion == 0 {
		out.minVersion = MinSupportedVersion
	}
	if out.maxVersion == 0 {
		out.maxVersion = MaxSupportedVersion
	}
	if out.minVersion > out.maxVersion {
		return resolvedHostConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: host min_version exceeds max_version")
	}
	if out.timeout == 0 {
		out.timeout = DefaultRPCTimeout
	}
	if out.timeout <= 0 {
		return resolvedHostConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: host default timeout must be positive")
	}
	if out.maxPending == 0 {
		out.maxPending = MaxConcurrentRPCs
	}
	if out.maxPending < 1 {
		return resolvedHostConfig{}, NewRpcError(ErrorCodeInvalidArgument, "syntra: host max concurrent must be positive")
	}
	return out, nil
}

// Host is a responder-side Syntra session factory. The zero value is
// invalid; construct with OpenHost. A Host is safe for concurrent Serve
// calls (one per connection) and NotifyAll broadcasts.
type Host struct {
	cfg resolvedHostConfig

	mu     sync.Mutex
	conns  map[*hostConn]struct{}
	closed bool
}

// hostConn tracks one served connection for broadcast and teardown.
// wake signals the serve pump that queued outbound frames (expiry
// results, broadcasts) are ready even when no inbound frame arrived.
type hostConn struct {
	core    hostCore
	cancels map[uint64]*callCancel
	wake    chan struct{}
}

// callCancel is the abandon handle for one in-flight handler. It is a
// pointer so dispatch completion can tell its own entry apart from a
// newer entry reusing the same request ID (functions are not comparable
// in Go; pointers are).
type callCancel struct {
	stop context.CancelFunc
}

// OpenHost creates a responder session factory. It validates the config
// and opens nothing per connection yet; each Serve call opens and closes
// exactly one core.
func OpenHost(cfg HostConfig) (*Host, error) {
	rcfg, err := resolveHostConfig(cfg)
	if err != nil {
		return nil, err
	}
	return &Host{cfg: rcfg, conns: make(map[*hostConn]struct{})}, nil
}

// Serve runs one connection on t: exactly one ClientHello first, exactly
// one terminal handshake outcome (ServerReady or handshake error +
// close), then validated dispatch until ctx ends, the transport fails, a
// fatal protocol violation arrives, or the Host closes. Unknown methods
// answer UNIMPLEMENTED; handler failures answer their mapped code; the
// connection stays usable. ctx end cancels in-flight handlers and closes
// the connection. Serve returns nil on a clean handshake-completed close
// and the fatal error otherwise.
func (h *Host) Serve(ctx context.Context, t Transport) error {
	if h == nil {
		return NewRpcError(ErrorCodeInternal, "syntra: nil host")
	}
	h.mu.Lock()
	if h.closed {
		h.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: host closed")
	}
	h.mu.Unlock()

	core, err := newHostCore(h.cfg)
	if err != nil {
		return err
	}
	hc := &hostConn{core: core, cancels: make(map[uint64]*callCancel), wake: make(chan struct{}, 1)}
	h.mu.Lock()
	if h.closed {
		h.mu.Unlock()
		_ = core.close()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: host closed")
	}
	h.conns[hc] = struct{}{}
	h.mu.Unlock()
	defer func() {
		h.mu.Lock()
		delete(h.conns, hc)
		h.mu.Unlock()
		_ = core.close()
	}()

	serveCtx, stop := context.WithCancel(ctx)
	defer stop()

	if err := h.serveHandshake(serveCtx, t, hc); err != nil {
		return err
	}
	return h.serveLoop(serveCtx, t, hc)
}

// serveHandshake runs the hello/policy/ready exchange.
func (h *Host) serveHandshake(ctx context.Context, t Transport, hc *hostConn) error {
	raw, err := t.Recv(ctx)
	if err != nil {
		if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
			return ctx.Err()
		}
		return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: handshake recv: %v", err))
	}
	version, herr := hc.core.acceptHello(raw)
	if herr != nil {
		return herr
	}
	_ = version
	hello, uerr := UnmarshalFrame(raw)
	if uerr != nil {
		return uerr
	}
	policy := h.cfg.policy
	if policy == nil {
		return NewRpcError(ErrorCodeUnauthenticated, "syntra: no credential policy configured")
	}
	principal, perr := policy(ctx, hello.GetHello().GetCredential())
	if perr != nil {
		var rerr *RpcError
		if errors.As(perr, &rerr) {
			return rerr
		}
		return NewRpcError(ErrorCodeInternal, "syntra: credential policy failed")
	}
	readyFrame, aerr := hc.core.authComplete(principal)
	if aerr != nil {
		return aerr
	}
	if serr := t.Send(ctx, readyFrame); serr != nil {
		if errors.Is(serr, context.Canceled) || errors.Is(serr, context.DeadlineExceeded) {
			return ctx.Err()
		}
		return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: handshake send: %v", serr))
	}
	return nil
}

// serveLoop dispatches validated requests to the handler and streams
// terminal results and notifications until the connection ends. Queued
// outbound frames that arise without inbound traffic (expiry results,
// broadcasts) are flushed on the wake signal and on a reap tick, so a
// silent peer still observes budgets and broadcasts.
func (h *Host) serveLoop(ctx context.Context, t Transport, hc *hostConn) error {
	if err := h.flush(ctx, t, hc); err != nil {
		return err
	}
	pumpCtx, pumpStop := context.WithCancel(context.Background())
	defer pumpStop()
	go func() {
		select {
		case <-ctx.Done():
			pumpStop()
		case <-pumpCtx.Done():
		}
	}()
	recvCh := make(chan recvResult, 1)
	go func() {
		for {
			raw, err := t.Recv(pumpCtx)
			select {
			case recvCh <- recvResult{raw: raw, err: err}:
			case <-pumpCtx.Done():
				return
			}
			if err != nil {
				return
			}
		}
	}()
	ticker := time.NewTicker(pumpTick)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			h.cancelHandlers(hc, nil, true)
			return nil
		case <-hc.wake:
			if err := h.flush(ctx, t, hc); err != nil {
				h.cancelHandlers(hc, nil, true)
				return err
			}
		case <-ticker.C:
			h.reapHandlers(ctx, hc)
			if err := h.flush(ctx, t, hc); err != nil {
				h.cancelHandlers(hc, nil, true)
				return err
			}
		case r := <-recvCh:
			if r.err != nil {
				h.cancelHandlers(hc, nil, true)
				if ctx.Err() != nil || errors.Is(r.err, context.Canceled) || errors.Is(r.err, context.DeadlineExceeded) {
					return nil
				}
				var rerr *RpcError
				if errors.As(r.err, &rerr) {
					return r.err
				}
				if errors.Is(r.err, io.EOF) {
					return nil
				}
				return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: recv: %v", r.err))
			}
			responses, cancelIDs, fatal := hc.core.onFrame(r.raw)
			if fatal != nil {
				h.cancelHandlers(hc, nil, true)
				return fatal
			}
			for _, id := range cancelIDs {
				h.cancelHandler(hc, id)
			}
			for _, resp := range responses {
				if serr := t.Send(ctx, resp); serr != nil {
					h.cancelHandlers(hc, nil, true)
					if ctx.Err() != nil {
						return nil
					}
					return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: send: %v", serr))
				}
			}
			for {
				id, req, ok := hc.core.takePending()
				if !ok {
					break
				}
				h.dispatch(ctx, t, hc, id, req)
			}
			h.reapHandlers(ctx, hc)
			if err := h.flush(ctx, t, hc); err != nil {
				h.cancelHandlers(hc, nil, true)
				return err
			}
		}
	}
}

// validSuccess reports whether res is a usable success outcome: valid
// and carrying a selected payload (empty counts; missing does not).
func validSuccess(res *RpcResult) bool {
	if res == nil || ValidateResult(res) != nil {
		return false
	}
	return res.GetPayload() != nil
}

// dispatch runs one validated request on the handler with the effective
// budget and answers exactly once. Completion wins over a concurrent
// cancel or budget expiry: a handler that returns success delivers
// success; a handler that abandons after cancel answers CANCELLED; a
// handler still running at budget expiry answers DEADLINE_EXCEEDED.
func (h *Host) dispatch(ctx context.Context, t Transport, hc *hostConn, id uint64, req *RpcRequest) {
	budget := h.cfg.timeout
	if req.GetTimeoutMs() > 0 {
		budget = time.Duration(req.GetTimeoutMs()) * time.Millisecond
	}
	hctx, stop := context.WithTimeout(ctx, budget)
	cc := &callCancel{stop: stop}
	h.mu.Lock()
	hc.cancels[id] = cc
	h.mu.Unlock()
	go func() {
		defer func() {
			h.mu.Lock()
			if cur, ok := hc.cancels[id]; ok && cur == cc {
				delete(hc.cancels, id)
			}
			h.mu.Unlock()
			stop()
		}()
		handler := h.cfg.handler
		var out *RpcResult
		if handler == nil {
			out = NewWireErrorResult(ErrorCodeUnimplemented, "syntra: unknown method")
		} else {
			res, herr := handler(hctx, req)
			if ctx.Err() != nil {
				// The connection is going away; drop the outcome.
				// In-flight correlation is reaped on teardown.
				return
			}
			if hctx.Err() != nil && !validSuccess(res) {
				// The per-call budget fired or the peer cancelled
				// while the handler ran, and the handler did not win
				// the race with a success. CANCELLED when the peer
				// asked; otherwise the budget owns the outcome
				// (SNTR-RPC-004/005).
				if hc.core.isCancelled(id) {
					out = NewWireErrorResult(ErrorCodeCancelled, "syntra: cancelled")
				} else {
					out = NewWireErrorResult(ErrorCodeDeadlineExceeded, "syntra: deadline exceeded")
				}
			} else {
				switch {
				case herr != nil:
					var rerr *RpcError
					if errors.As(herr, &rerr) {
						out = NewWireErrorResult(rerr.Code, rerr.Message)
					} else {
						out = NewWireErrorResult(ErrorCodeInternal, "syntra: internal error")
					}
				case validSuccess(res):
					// Completion wins, even against a concurrent
					// cancel or budget expiry (SNTR-RPC-005/031).
					out = res
				case res != nil:
					out = NewWireErrorResult(ErrorCodeInternal, "syntra: internal error")
				default:
					out = NewWireErrorResult(ErrorCodeInternal, "syntra: internal error")
				}
			}
		}
		resp, expired, aerr := hc.core.answer(id, out)
		if aerr != nil || expired {
			// Expired answers were already replaced by an automatic
			// DEADLINE_EXCEEDED result; validation failures here are
			// core bugs that must not kill the connection pump.
			h.flushDetached(ctx, t, hc)
			return
		}
		h.sendDetached(ctx, t, hc, resp)
	}()
}

// sendDetached transmits one frame from a handler goroutine. Transport
// implementations MUST be safe for concurrent Send; loopback and the
// socket adapters this binding targets are.
func (h *Host) sendDetached(ctx context.Context, t Transport, hc *hostConn, frame []byte) {
	if len(frame) == 0 {
		return
	}
	_ = t.Send(ctx, frame)
	h.flushDetached(ctx, t, hc)
}

// flushDetached drains queued outbound frames after an async answer.
func (h *Host) flushDetached(ctx context.Context, t Transport, hc *hostConn) {
	for {
		frame, ok := hc.core.nextOutbound()
		if !ok {
			return
		}
		if len(frame) == 0 {
			continue
		}
		if err := t.Send(ctx, frame); err != nil {
			return
		}
	}
}

// flush drains queued outbound frames on the serve pump.
func (h *Host) flush(ctx context.Context, t Transport, hc *hostConn) error {
	for {
		frame, ok := hc.core.nextOutbound()
		if !ok {
			return nil
		}
		if len(frame) == 0 {
			continue
		}
		if err := t.Send(ctx, frame); err != nil {
			if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
				return nil
			}
			return NewRpcError(ErrorCodeUnavailable, fmt.Sprintf("syntra: send: %v", err))
		}
	}
}

// reapHandlers abandons handlers whose budgets expired; the core already
// auto-enqueued their DEADLINE_EXCEEDED results.
func (h *Host) reapHandlers(_ context.Context, hc *hostConn) {
	expired := hc.core.reapExpired(time.Now())
	h.cancelHandlers(hc, expired, false)
}

// cancelHandler abandons one handler after a peer cancel.
func (h *Host) cancelHandler(hc *hostConn, id uint64) {
	h.mu.Lock()
	cc, ok := hc.cancels[id]
	h.mu.Unlock()
	if ok {
		cc.stop()
	}
}

// cancelHandlers abandons handlers: exactly ids, or every in-flight
// handler when all is true. all exists because a nil ids slice is
// ambiguous (reapExpiry returns nil both when nothing expired and when
// the core is gone); callers MUST pass all=false for reap results.
func (h *Host) cancelHandlers(hc *hostConn, ids []uint64, all bool) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if all {
		for id, cc := range hc.cancels {
			cc.stop()
			delete(hc.cancels, id)
		}
		return
	}
	for _, id := range ids {
		if cc, ok := hc.cancels[id]; ok {
			cc.stop()
			delete(hc.cancels, id)
		}
	}
}

// NotifyAll enqueues payload as a notification on every served
// connection. With no connections it is a documented no-op. Payloads
// MUST be opaque application bytes; empty is a valid empty event.
func (h *Host) NotifyAll(payload []byte) error {
	if h == nil {
		return NewRpcError(ErrorCodeInternal, "syntra: nil host")
	}
	if err := ValidatePayloadSize(len(payload)); err != nil {
		return err
	}
	h.mu.Lock()
	if h.closed {
		h.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: host closed")
	}
	conns := make([]*hostConn, 0, len(h.conns))
	for hc := range h.conns {
		conns = append(conns, hc)
	}
	h.mu.Unlock()
	for _, hc := range conns {
		_ = hc.core.notify(payload)
		select {
		case hc.wake <- struct{}{}:
		default:
		}
	}
	return nil
}

// Close releases the factory: new Serve calls fail fast and served
// connections are abandoned (their handlers observe ctx cancellation via
// the Serve ctx, and transports stay owned by their callers). A second
// Close reports FailedPrecondition.
func (h *Host) Close() error {
	if h == nil {
		return NewRpcError(ErrorCodeInternal, "syntra: nil host")
	}
	h.mu.Lock()
	if h.closed {
		h.mu.Unlock()
		return NewRpcError(ErrorCodeFailedPrecondition, "syntra: host already closed")
	}
	h.closed = true
	h.mu.Unlock()
	return nil
}
