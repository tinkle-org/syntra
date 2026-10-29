# Transport Selection Guide

Syntra's core is identical on every transport; profiles differ only in
framing, handshake binding, auth carriage, failure mapping, and security
properties. Choose by deployment constraints, not by application domain —
no profile is "for" any particular kind of app.

Conformance note: claiming Core requires passing over at least one
transport profile; no implementation must support every transport
(`conformance/profiles.yaml`). Production claims MUST name only secure
profiles.

## Current baseline profiles

The profiles below retain the baseline TLS requirements and existing
executable conformance scope. Delivered experimental SC1 draft-1 carriers
are described separately below; they do not replace these profile definitions.

### TLS over TCP (`SNTR-TLS-TCP-V1`, secure)

A persistent, low-level bidirectional byte stream: 4-byte big-endian
length prefix + serialized `Frame`, strict stream parsing, no magic bytes.
Choose when both peers hold long-lived connections and you want minimal
framing overhead with full-duplex RPC, cancellation, and server push over
one channel. Requires managing TLS certificates and a TCP-reachable port.

### HTTPS (`SNTR-HTTPS-H1-V1` / `SNTR-HTTPS-H2-V1`, secure)

Request/response RPC (`POST /syntra/v1/rpc`, one `Frame` per body) that is
proxy-, firewall-, and load-balancer-friendly: standard ports, standard
TLS termination, and per-exchange authentication fit existing web
infrastructure. H1 gives strictly sequential exchanges per connection;
H2 multiplexes independent concurrent RPCs as streams on one connection
(with stream-aware failure mapping — `REFUSED_STREAM` and streams above a
received `GOAWAY` last-stream-ID prove non-execution; unfinished streams at or
below it remain outcome-unknown absent another definitive signal). Retry follows
the profile's idempotency/key, fresh-ID, and bounded-backoff rules; `GOAWAY`
also forbids new streams on the draining connection. No server push exists on these profiles:
each exchange is one independent logical connection. Choose when operating
behind web infrastructure, or when per-request isolation matches your
auth model.

### Secure WebSocket (`SNTR-WSS-H1-V1`, secure)

A persistent bidirectional channel over HTTP/1.1 Upgrade
(`/syntra/v1/ws`, `syntra.v1` subprotocol; one binary message = one
`Frame`, binary only). Browser- and proxy-friendly where raw TCP is
blocked but HTTP Upgrade passes, with real-time duplex including server
events. Requires the same certificate discipline as HTTPS plus WebSocket
close-code and Ping/Pong handling.

### Plain TCP / HTTP / WebSocket (development only)

`SNTR-TCP-V1`, `SNTR-HTTP-V1`, `SNTR-WS-V1` are byte-identical in
mapping to their secure counterparts minus TLS. Use only in trusted
environments (loopback or isolated test networks, no public routing) with
throwaway credentials — typically for conformance runs, offline protocol
experiments, and debugging with packet captures. Distributions MUST disable
them by default for production and warn when enabled. Never carry
production credentials or authority over them.

## Quick chooser

| Constraint | Fit |
|---|---|
| Long-lived duplex, lowest overhead | TLS/TCP |
| Web infrastructure, proxies, per-request isolation | HTTPS (H1 simple, H2 concurrent) |
| Browser clients or Upgrade-friendly networks + duplex/events | WSS |
| Offline tests, conformance, captures | Plain profile matching your secure target |

Deferred transports (UDP, DTLS, QUIC, HTTP/3, QUIC DATAGRAM, WebSocket
over HTTP/2 Extended CONNECT) MUST NOT be described as implemented; they
are future extensions only.

## Experimental SC1 draft-1: choose the carrier separately

[Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
selects transport-independent Syntra Secure Channel v1 (SC1). The Go
implementation delivers bounded TCP/WS/WSS in bootstrap NK and returning
NKpsk0 modes. Its [contract and implementation status](sc1-implementation.md#implementation-status)
are experimental; RFC 0007 and Proposed ADR-011 remain unaccepted and the
production TLS policy above is unchanged.

| Carrier | Delivered mapping and integration concern |
|---|---|
| TCP | u16BE length for every M1/M2/record message; encrypted inner u32BE frame stream. Packet boundaries have no protocol meaning. |
| WS | One binary message per M1/M2/record, no SC1 u16 prefix; compression disabled, exact `syntra.sc1.draft1` subprotocol. |
| WSS | Same SC1 message mapping with independently verified outer TLS ≥1.3 and the provisioned Noise server pin. |
| UDP | Deferred; no datagram binding, reliability, replay window or roaming support is implemented. |
| HTTP/HTTPS request-response | Excluded from this implementation. HTTP serves only the WS upgrade; baseline request-response specifications retain their meaning. |

The versioned public context binds mode, carrier, server-key ID, epoch,
independent eight-byte handle and exact UTF-8 scope. Both Noise payloads are
empty. Record ciphertext is 17–65,535 bytes; serialized frames are 1–1,048,576
bytes and may span records. Clear framing is not AEAD AD. Existing WS/WSS
identifiers and `syntra.v1` bytes must not be silently reinterpreted.

Choose explicit endpoints, modes and provisioning. Dial refuses redirects;
standard inspectable HTTP transports enforce certificate verification and
TLS ≥1.3, while custom RoundTrippers own TLS policy. Accept binds WS/WSS to
`r.TLS`, not forwarded headers. There is no automatic downgrade or fallback.
Servers own TLS, origin admission and HTTP header limits/timeouts.

High-level dial returns after core ready within a 10s total establishment
budget, shortened by the caller. Adapter handshake/write/record/frame limits
default to 5s and may only be shortened; lifetime defaults/maxes at 24h,
with 2^32 records per direction as an additional channel ceiling. Operation
admission defaults to 32 per direction (maximum 1,024). A record's assembly
clock begins on its first wire byte; a frame's clock begins on its first
authenticated prefix byte, without trickle refresh. See
[operational limits](sc1-implementation.md#operational-limits) for ownership,
server admission and shutdown qualifications.

Bootstrap does not enroll a client implicitly. Returning authentication still
requires explicit [host policy](sc1-implementation.md#authentication-boundary),
hello/ready and per-method authorization. Provisioning/storage/rotation and
RPC retry safety remain application responsibilities.

[Verification evidence](sc1-implementation.md#verification-evidence) includes
same-implementation Docker tests across six carrier/mode groups. High-level
connection orchestration has local unit coverage, not container coverage.
Neither establishes independent wire interoperability or formal `CONF-*`
conformance. [In-memory benchmarks](perf-tradeoffs.md) do not establish network
deployment performance; independent review and interoperability remain open.
