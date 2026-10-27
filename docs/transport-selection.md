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
executable conformance scope. The selected SC1 proposal is described
separately at the end of this guide; it adds no current transport support.

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

## Selected SC1 proposal: choose the carrier separately

[Draft RFC 0007](../rfcs/0007-secure-channel-device-authorization.md)
selects transport-independent Syntra Secure Channel v1 (SC1), with one
[secure-channel state machine](../specifications/security/secure-channel.md)
and proposed [TCP, UDP, and WebSocket bindings](../specifications/transports/noise-bindings.md).
It is not Accepted and does not replace the chooser above. The protocol
core does not dial sockets or require WebSocket or gRPC.

| Proposed carrier | Integration concern |
|---|---|
| TCP | Keep stream framing and bounded record parsing in the binding. SC1 records are distinct from the baseline plaintext `Frame` stream. |
| UDP | Define datagram record boundaries, loss/reorder handling, and resource limits in the binding. A proposed carrier does not imply implemented UDP or reliable RPC delivery. |
| WebSocket | Carry SC1 on a distinct wire binding; do not reinterpret existing WS/WSS profile IDs or the `syntra.v1` one-message/one-`Frame` mapping. Browser `wss://` still needs outer TLS. |

Existing HTTPS/WSS TLS compatibility stays available. SC1's NK enrollment
and NKpsk0 returning-device authentication do not replace host-owned
[device policy](../specifications/security/device-authorization.md),
Syntra hello/ready, or RPC retry discipline. Empty M1/M2 payloads carry
no application data or credentials; the host verifies the first
authenticated client transport record before protected actions.

The 96-byte NK handshake-body total and 104 = 96 + 8-byte returning total
(including `auth_id`) exclude framing and extra epoch/version fields.
They are not full establishment RTTs or transport benchmarks; see
[the size accounting](perf-tradeoffs.md#5-sc1-handshake-size-accounting-proposal-only).
The [SC1 conformance plan](../conformance/plans/secure-channel.md) is future
verification, not an addition to today's executable profiles.
