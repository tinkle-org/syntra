package syntra

import (
	"context"
	"testing"
	"time"
)

// TestMemoryStoreAtomicFailure covers persistence failure: a failing write
// records nothing and the last persisted position is retained for retry.
func TestMemoryStoreAtomicFailure(t *testing.T) {
	s := NewMemoryStore()
	pos := CommittedPosition{Stream: "s", Generation: 7, Committed: []byte("c-43")}
	if err := s.StoreAtomic(pos, []byte("fx-1")); err != nil {
		t.Fatal(err)
	}
	s.FailNext = true
	bad := CommittedPosition{Stream: "s", Generation: 7, Committed: []byte("c-44")}
	if err := s.StoreAtomic(bad, []byte("fx-2")); err == nil {
		t.Fatal("failing write must error")
	}
	got := s.Load("s")
	if got == nil || string(got.Committed) != "c-43" {
		t.Fatalf("last persisted must be retained, got %v", got)
	}
	if err := s.StoreAtomic(bad, []byte("fx-2")); err != nil {
		t.Fatal(err)
	}
	if got := s.Load("s"); string(got.Committed) != "c-44" {
		t.Fatalf("retry must advance, got %v", got)
	}
}

// TestDuplicateCacheBounded covers bounded duplicate suppression: hits avoid
// re-apply, overflow evicts oldest first.
func TestDuplicateCacheBounded(t *testing.T) {
	c := NewDuplicateCache(2)
	c.Insert([]byte("a"))
	c.Insert([]byte("b"))
	if !c.Contains([]byte("a")) {
		t.Fatal("expected hit")
	}
	c.Insert([]byte("c"))
	if c.Contains([]byte("a")) {
		t.Fatal("oldest must be evicted first")
	}
	if !c.Contains([]byte("b")) || !c.Contains([]byte("c")) {
		t.Fatal("recent entries must be retained")
	}
	if c.Len() != 2 {
		t.Fatalf("len = %d, want 2", c.Len())
	}
}

// TestStagedSnapshotFailure covers snapshot failure: incomplete install
// fails without advancing, boundary mismatch fails.
func TestStagedSnapshotFailure(t *testing.T) {
	s, err := NewStagedSnapshot([]byte("h1"), []byte("b-100"), 2, 1024)
	if err != nil {
		t.Fatal(err)
	}
	if err := s.StagePage(0, []byte("half"), []byte("b-100")); err != nil {
		t.Fatal(err)
	}
	if _, err := s.Install(); err == nil {
		t.Fatal("incomplete install must fail")
	}
	if err := s.StagePage(1, []byte("x"), []byte("other")); err == nil {
		t.Fatal("boundary mismatch must fail")
	}
	if err := s.StagePage(1, []byte("rest"), []byte("b-100")); err != nil {
		t.Fatal(err)
	}
	out, err := s.Install()
	if err != nil || string(out) != "halfrest" {
		t.Fatalf("install = %q, %v", out, err)
	}
}

// TestDirectedDeliveryIsolation covers targeted delivery: a batch routed to
// one principal is never visible to another (no NotifyAll broadcast).
func TestDirectedDeliveryIsolation(t *testing.T) {
	pA := newPair(t, testClientConfig(), testHostConfig())
	defer pA.Cleanup()
	pB := newPair(t, testClientConfig(), testHostConfig())
	defer pB.Cleanup()

	// Directed send at a non-member principal is a no-op for both pairs.
	if err := pA.host.NotifyDirected("no-such-principal", []byte("x")); err != nil {
		t.Fatal(err)
	}
	select {
	case ntf := <-pA.client.Notifications():
		t.Fatalf("isolation violated: untargeted notification arrived: %q", ntf.GetPayload())
	case <-time.After(150 * time.Millisecond):
	}
	select {
	case ntf := <-pB.client.Notifications():
		t.Fatalf("isolation violated on peer: %q", ntf.GetPayload())
	case <-time.After(150 * time.Millisecond):
	}

	// Broadcast still works as the non-recovery path; drivers must not use
	// it for recovery batches.
	if err := pA.host.NotifyAll([]byte("broadcast-ok")); err != nil {
		t.Fatal(err)
	}
	select {
	case ntf := <-pA.client.Notifications():
		if string(ntf.GetPayload()) != "broadcast-ok" {
			t.Fatalf("broadcast = %q", ntf.GetPayload())
		}
	case <-time.After(3 * time.Second):
		t.Fatal("broadcast never arrived")
	}
}

// TestCheckpointReconciliationIdlePeers covers bounded checkpoint
// reconciliation: a missing final update is discovered without requiring
// another update, while idle peers stay quiet once converged. Tick is
// independently scheduled (interval-gated) and bounded per tick.
func TestCheckpointReconciliationIdlePeers(t *testing.T) {
	rec := NewCheckpointReconciler(ReconcilerConfig{TickInterval: 0, MaxStreamsPerTick: 8})
	rec.NoteObserved(Checkpoint{Stream: "s", Generation: 7, Base: []byte("c-40"), Result: []byte("c-43")})
	committed := map[string][]byte{"s": []byte("c-40")}
	lookup := func(stream string) ([]byte, bool) {
		b, ok := committed[stream]
		return b, ok
	}
	found := rec.Tick(time.Now(), lookup)
	if len(found) != 1 || found[0] != "s" {
		t.Fatalf("reconciliation must discover missing final update, got %v", found)
	}
	committed["s"] = []byte("c-43")
	if found := rec.Tick(time.Now(), lookup); len(found) != 0 {
		t.Fatalf("converged streams must stay quiet, got %v", found)
	}
}

// TestReconcilerBoundedTick covers the per-tick bound and schedule gate.
func TestReconcilerBoundedTick(t *testing.T) {
	rec := NewCheckpointReconciler(ReconcilerConfig{TickInterval: time.Hour, MaxStreamsPerTick: 1})
	rec.NoteObserved(Checkpoint{Stream: "a", Result: []byte("r1")})
	rec.NoteObserved(Checkpoint{Stream: "b", Result: []byte("r2")})
	lookup := func(stream string) ([]byte, bool) { return []byte("old"), true }
	if got := rec.Tick(time.Now(), lookup); len(got) != 1 {
		t.Fatalf("tick must be bounded to 1, got %v", got)
	}
	if got := rec.Tick(time.Now(), lookup); len(got) != 0 {
		t.Fatalf("schedule gate must suppress close ticks, got %v", got)
	}
}

// TestLossTotalsCumulativeNoDoubleCount covers unified loss semantics on the
// public queue: cumulative counts/bytes advance exactly once per drop and
// loss-change wakeups observe the same totals without double-counting.
func TestLossTotalsCumulativeNoDoubleCount(t *testing.T) {
	p := newPair(t, testClientConfig(), testHostConfig())
	defer p.Cleanup()
	d0, b0 := p.client.LossTotals()
	for i := 0; i < 64; i++ {
		_ = p.host.NotifyAll([]byte("x"))
	}
	deadline := time.Now().Add(3 * time.Second)
	for {
		if d, _ := p.client.LossTotals(); d != d0 {
			break
		}
		if time.Now().After(deadline) {
			d, b := p.client.LossTotals()
			t.Fatalf("loss totals never advanced (d0=%d b0=%d totals=(%d,%d))", d0, b0, d, b)
		}
		time.Sleep(10 * time.Millisecond)
	}
	d1, b1 := p.client.LossTotals()
	if d1 <= d0 {
		t.Fatalf("dropped did not advance: %d -> %d", d0, d1)
	}
	if b1 <= b0 {
		t.Fatalf("dropped bytes did not advance: %d -> %d", b0, b1)
	}
	if got := p.client.DroppedNotifications(); got != d1-pureGoCoreDropped(p.client) {
		t.Fatalf("public drops inconsistent: public=%d totals=(%d,%d)", got, d1, b1)
	}
	// Late subscriber with stale totals returns immediately with current
	// totals and no error (no double-counting, no missed signal).
	ctx, stop := context.WithTimeout(context.Background(), 3*time.Second)
	defer stop()
	d2, b2, err := p.client.WaitLossChange(ctx, d0, b0)
	if err != nil {
		t.Fatalf("WaitLossChange with stale totals = %d,%d,%v", d2, b2, err)
	}
	if d2 != d1 || b2 != b1 {
		t.Fatalf("WaitLossChange = (%d,%d), want current totals (%d,%d)", d2, b2, d1, b1)
	}
	// A waiter already at current totals blocks: with no further loss it
	// ends via ctx expiry (wakeups fire on change, not spuriously).
	short, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()
	if _, _, err := p.client.WaitLossChange(short, d1, b1); err == nil {
		t.Fatal("WaitLossChange at current totals must block until change or ctx end")
	}
}

// pureGoCoreDropped returns core-layer drops for the consistency check
// above (zero under the native adapter when the FFI core holds them).
func pureGoCoreDropped(c *Client) uint64 {
	if c == nil || c.core == nil {
		return 0
	}
	d, _ := c.core.lossTotals()
	return d
}
