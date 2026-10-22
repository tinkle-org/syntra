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

func TestReliableReconciliation(t *testing.T) {
	m := testReliableManager(t)
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
