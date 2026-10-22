package syntra

import (
	"testing"
	"time"
)

func testReliableManager(t *testing.T) *ReliableManager {
	t.Helper()
	m, err := NewReliableManager(DefaultControlBounds())
	if err != nil {
		t.Fatal(err)
	}
	return m
}

func TestReliableSessionIdentityDistinct(t *testing.T) {
	if _, err := ValidateSessionID(make([]byte, 15)); err == nil {
		t.Fatal("short session id accepted")
	}
	if _, err := ValidateSessionID(make([]byte, 16)); err == nil {
		t.Fatal("zero session id accepted")
	}
	ok := make([]byte, 16)
	for i := range ok {
		ok[i] = byte(i + 1)
	}
	if _, err := ValidateSessionID(ok); err != nil {
		t.Fatalf("valid session id rejected: %v", err)
	}
}

func TestReliableEpochFencing(t *testing.T) {
	if err := ValidateEpoch(0); err == nil {
		t.Fatal("zero epoch accepted")
	}
	if err := CheckEpochAdvance(3, 3); err == nil {
		t.Fatal("stale epoch accepted")
	}
	if _, err := NextEpoch(^uint64(0)); err == nil {
		t.Fatal("epoch wrap accepted")
	}
}

func TestReliableLeaseNegotiation(t *testing.T) {
	got, err := NegotiateLease(LeaseProposal{})
	if err != nil {
		t.Fatal(err)
	}
	if got.KeepaliveIntervalMs >= got.IdleTimeoutMs {
		t.Fatal("keepalive not below idle")
	}
	if _, err := NegotiateLease(LeaseProposal{IdleTimeoutMs: 1, KeepaliveIntervalMs: 1000}); err == nil {
		t.Fatal("under-minimum idle accepted")
	}
}

func TestReliableAttachFencesOld(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, epoch, cred, _ := mustCreate(t, m, now)
	if epoch != 1 {
		t.Fatalf("epoch = %d, want 1", epoch)
	}
	if _, _, _, _, err := m.Attach(now, sid, nil, "conn-1", "svc-a", 1, LeaseProposal{}); err != nil {
		t.Fatalf("first attach: %v", err)
	}
	epoch2, _, fenced, fresh, err := m.Attach(now, sid, cred, "conn-2", "svc-a", 1, LeaseProposal{})
	if err != nil {
		t.Fatalf("resume: %v", err)
	}
	if epoch2 != 2 || fenced != "conn-1" {
		t.Fatalf("epoch2=%d fenced=%q", epoch2, fenced)
	}
	if len(fresh) == 0 {
		t.Fatal("resume did not rotate credential")
	}
	if _, _, _, _, err := m.Attach(now, sid, cred, "conn-3", "svc-a", 1, LeaseProposal{}); err == nil {
		t.Fatal("rotated handle replay accepted")
	}
	epoch3, _, fenced3, fresh3, err := m.Attach(now, sid, fresh, "conn-3", "svc-a", 1, LeaseProposal{})
	if err != nil {
		t.Fatalf("second resume with rotated credential: %v", err)
	}
	if epoch3 != 3 || fenced3 != "conn-2" {
		t.Fatalf("epoch3=%d fenced=%q, want 3/conn-2", epoch3, fenced3)
	}
	if len(fresh3) == 0 || string(fresh3) == string(fresh) {
		t.Fatal("second resume did not rotate credential")
	}
}

func mustCreate(t *testing.T, m *ReliableManager, now time.Time) (SessionID, uint64, []byte, ConfirmedLease) {
	t.Helper()
	sid, epoch, cred, lease, err := m.CreateSession(now, "svc-a", 1, LeaseProposal{})
	if err != nil {
		t.Fatal(err)
	}
	return sid, epoch, cred, lease
}

func TestReliableReconciliation(t *testing.T) {	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	if _, _, _, _, err := m.Attach(now, sid, nil, "conn-1", "svc-a", 1, LeaseProposal{}); err != nil {
		t.Fatal(err)
	}
	var did DeliveryID
	for i := range did {
		did[i] = 7
	}
	if out, _, err := m.Reconcile(now, sid, did); err != nil || out != ReconcileUnknown {
		t.Fatalf("out=%v err=%v", out, err)
	}
	okOutcome := StoredOutcome{Payload: []byte("hello")}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("hello"), okOutcome); err != nil {
		t.Fatal(err)
	}
	if out, stored, err := m.Reconcile(now, sid, did); err != nil || out != ReconcileRetained || stored == nil {
		t.Fatalf("out=%v err=%v", out, err)
	}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("different"), okOutcome); err == nil {
		t.Fatal("mismatched content accepted")
	}
}

func TestReliableSignalsMapToExistingCodes(t *testing.T) {
	if SignalCode(SignalOverloaded) != ErrorCodeResourceExhausted {
		t.Fatal("overloaded must map to RESOURCE_EXHAUSTED")
	}
	if SignalCode(SignalFenced) != ErrorCodeFailedPrecondition {
		t.Fatal("fenced must map to FAILED_PRECONDITION")
	}
	if _, err := ParseSessionSignal("nope"); err == nil {
		t.Fatal("unknown signal accepted")
	}
}

func TestReliableZeroDeliveryIDRejected(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var zero DeliveryID
	if _, err := m.RecordResult(now, sid, zero, "/example.Echo/Echo", []byte("x"), StoredOutcome{Payload: []byte("x")}); err == nil {
		t.Fatal("zero delivery id accepted by RecordResult")
	}
	if _, _, err := m.Reconcile(now, sid, zero); err == nil {
		t.Fatal("zero delivery id accepted by Reconcile")
	}
	if err := m.RecordTombstone(now, sid, zero, ErrorCodeDeadlineExceeded); err == nil {
		t.Fatal("zero delivery id accepted by RecordTombstone")
	}
	if _, _, err := m.TombstoneOf(now, sid, zero); err == nil {
		t.Fatal("zero delivery id accepted by TombstoneOf")
	}
	if _, err := m.Forget(sid, zero); err == nil {
		t.Fatal("zero delivery id accepted by Forget")
	}
}

func TestReliableIdleTimeoutDetaches(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	lease, err := NegotiateLease(LeaseProposal{IdleTimeoutMs: 2000, KeepaliveIntervalMs: 1000})
	if err != nil {
		t.Fatal(err)
	}
	_ = lease
	if _, _, _, _, err := m.Attach(now, sid, nil, "conn-1", "svc-a", 1, LeaseProposal{IdleTimeoutMs: 2000, KeepaliveIntervalMs: 1000}); err != nil {
		t.Fatal(err)
	}
	if idle, err := m.CheckIdle(now, sid); err != nil || idle {
		t.Fatalf("fresh session must not be idle: idle=%v err=%v", idle, err)
	}
	later := now.Add(2100 * time.Millisecond)
	if idle, err := m.CheckIdle(later, sid); err != nil || !idle {
		t.Fatalf("stale session must be idle: idle=%v err=%v", idle, err)
	}
	swept, err := m.SweepIdle(later)
	if err != nil {
		t.Fatalf("SweepIdle: %v", err)
	}
	if len(swept) != 1 || swept[0] != sid {
		t.Fatalf("SweepIdle = %v, want [%v]", swept, sid)
	}
	signals := m.DrainSignals(16)
	found := false
	for _, s := range signals {
		if s.ID == sid && s.Signal == SignalIdleTimeout {
			found = true
		}
	}
	if !found {
		t.Fatalf("IdleTimeout signal missing: %v", signals)
	}
	// Reap path also enforces idle: re-attach, go stale, reap, expect detach.
	if _, _, _, _, err := m.Attach(later, sid, nil, "conn-2", "svc-a", 1, LeaseProposal{IdleTimeoutMs: 2000, KeepaliveIntervalMs: 1000}); err != nil {
		t.Fatal(err)
	}
	m.ReapExpired(later.Add(2100 * time.Millisecond))
	stillIdle, err := m.CheckIdle(later.Add(2100*time.Millisecond), sid)
	if err != nil {
		t.Fatal(err)
	}
	if stillIdle {
		t.Fatal("reap must have detached the idle active")
	}
}

func TestReliableFencedSignalFullQueue(t *testing.T) {
	bounds := DefaultControlBounds()
	bounds.MaxControlQueue = 1
	bounds.MaxControlBytes = 64
	m, err := NewReliableManager(bounds)
	if err != nil {
		t.Fatal(err)
	}
	now := time.Now()
	sid, _, cred, _ := mustCreate(t, m, now)
	if _, _, _, _, err := m.Attach(now, sid, nil, "conn-1", "svc-a", 1, LeaseProposal{}); err != nil {
		t.Fatal(err)
	}
	// Fill the control queue so the Fenced signal has nowhere to go.
	if err := m.Signal(sid, SignalOverloaded); err != nil {
		t.Fatal(err)
	}
	if _, _, _, _, err := m.Attach(now, sid, cred, "conn-2", "svc-a", 1, LeaseProposal{}); err == nil {
		t.Fatal("attach with full control queue must propagate ResourceExhausted, not swallow Fenced")
	} else if rerr, ok := err.(*RpcError); !ok || rerr.Code != ErrorCodeResourceExhausted {
		t.Fatalf("attach full-queue = %v, want RESOURCE_EXHAUSTED", err)
	}
}

func TestReliableDrainForShutdownReportsDropped(t *testing.T) {
	bounds := DefaultControlBounds()
	bounds.MaxControlQueue = 1
	bounds.MaxControlBytes = 64
	m, err := NewReliableManager(bounds)
	if err != nil {
		t.Fatal(err)
	}
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	if _, _, _, _, err := m.Attach(now, sid, nil, "conn-1", "svc-a", 1, LeaseProposal{}); err != nil {
		t.Fatal(err)
	}
	if err := m.Signal(sid, SignalOverloaded); err != nil {
		t.Fatal(err)
	}
	ids, signals, derr := m.DrainForShutdown()
	if derr == nil {
		t.Fatal("DrainForShutdown with full queue must report the dropped GoingAway signal")
	}
	if len(ids) != 1 {
		t.Fatalf("drained ids = %v", ids)
	}
	_ = signals
}

func TestReliableExpiredRetainedReinsert(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var did DeliveryID
	for i := range did {
		did[i] = 9
	}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("one"), StoredOutcome{Payload: []byte("one")}); err != nil {
		t.Fatal(err)
	}
	later := now.Add(DefaultControlBounds().ResultRetention + time.Second)
	// Expired entry must not behave as a duplicate: the new insert with
	// different content succeeds and becomes Retained.
	if _, err := m.RecordResult(later, sid, did, "/example.Echo/Echo", []byte("two"), StoredOutcome{Payload: []byte("two")}); err != nil {
		t.Fatalf("expired retained must allow reinsert, got %v", err)
	}
	out, stored, err := m.Reconcile(later, sid, did)
	if err != nil || out != ReconcileRetained || stored == nil || string(stored.Payload) != "two" {
		t.Fatalf("reinsert = %v %v %v", out, stored, err)
	}
}

func TestReliableOutcomeDeepCopy(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var did DeliveryID
	for i := range did {
		did[i] = 11
	}
	payload := []byte("mutable")
	outcome := StoredOutcome{Payload: payload}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("m"), outcome); err != nil {
		t.Fatal(err)
	}
	payload[0] = 'X'
	outcome.Payload[0] = 'X'
	_, stored, err := m.Reconcile(now, sid, did)
	if err != nil || stored == nil {
		t.Fatal(err)
	}
	if string(stored.Payload) == "Xutable" {
		t.Fatal("RecordResult aliased caller payload")
	}
	stored.Payload[0] = 'Z'
	_, stored2, err := m.Reconcile(now, sid, did)
	if err != nil || stored2 == nil {
		t.Fatal(err)
	}
	if stored2.Payload[0] == 'Z' {
		t.Fatal("Reconcile returned aliased retained bytes")
	}
	// Err pointer aliasing: mutating the caller's RpcError must not affect
	// retained state, and vice versa.
	var did2 DeliveryID
	for i := range did2 {
		did2[i] = 12
	}
	rerr := NewRpcError(ErrorCodeNotFound, "orig")
	if _, err := m.RecordResult(now, sid, did2, "/example.Echo/Echo", []byte("m"), StoredOutcome{Err: rerr}); err != nil {
		t.Fatal(err)
	}
	rerr.Message = "mutated"
	_, stored3, err := m.Reconcile(now, sid, did2)
	if err != nil || stored3 == nil || stored3.Err == nil {
		t.Fatal(err)
	}
	if stored3.Err.Message == "mutated" {
		t.Fatal("RecordResult aliased caller RpcError")
	}
}

func TestReliableInsertClearsForgotten(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var did DeliveryID
	for i := range did {
		did[i] = 13
	}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("x"), StoredOutcome{Payload: []byte("x")}); err != nil {
		t.Fatal(err)
	}
	if _, err := m.Forget(sid, did); err != nil {
		t.Fatal(err)
	}
	if out, _, _ := m.Reconcile(now, sid, did); out != ReconcileForgotten {
		t.Fatalf("after forget = %v, want forgotten", out)
	}
	if _, err := m.RecordResult(now, sid, did, "/example.Echo/Echo", []byte("x"), StoredOutcome{Payload: []byte("x")}); err != nil {
		t.Fatal(err)
	}
	if out, _, _ := m.Reconcile(now, sid, did); out != ReconcileRetained {
		t.Fatalf("reinsert after forget = %v, want retained", out)
	}
}

func TestReliableExpiredTombstoneBecomesForgotten(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var did DeliveryID
	for i := range did {
		did[i] = 14
	}
	if err := m.RecordTombstone(now, sid, did, ErrorCodeDeadlineExceeded); err != nil {
		t.Fatal(err)
	}
	later := now.Add(DefaultControlBounds().TombstoneRetention + time.Second)
	out, _, err := m.Reconcile(later, sid, did)
	if err != nil || out != ReconcileForgotten {
		t.Fatalf("expired tombstone reconcile = %v %v, want forgotten", out, err)
	}
	if out2, _, _ := m.Reconcile(later, sid, did); out2 != ReconcileForgotten {
		t.Fatalf("second reconcile = %v, want forgotten", out2)
	}
}

func TestReliableTombstoneFirstWriteWins(t *testing.T) {
	m := testReliableManager(t)
	now := time.Now()
	sid, _, _, _ := mustCreate(t, m, now)
	var did DeliveryID
	for i := range did {
		did[i] = 15
	}
	if err := m.RecordTombstone(now, sid, did, ErrorCodeDeadlineExceeded); err != nil {
		t.Fatal(err)
	}
	if err := m.RecordTombstone(now, sid, did, ErrorCodeDeadlineExceeded); err != nil {
		t.Fatalf("same-code tombstone must be idempotent: %v", err)
	}
	if err := m.RecordTombstone(now, sid, did, ErrorCodeCancelled); err == nil {
		t.Fatal("code-mismatched tombstone must be rejected without overwriting")
	}
	code, ok, err := m.TombstoneOf(now, sid, did)
	if err != nil || !ok || code != ErrorCodeDeadlineExceeded {
		t.Fatalf("tombstone overwritten: code=%v ok=%v err=%v", code, ok, err)
	}
}
