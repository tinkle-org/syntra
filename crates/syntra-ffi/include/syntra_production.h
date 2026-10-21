#ifndef SYNTRA_PRODUCTION_H
#define SYNTRA_PRODUCTION_H

/* Syntra production native ABI (transport-agnostic frame pump).
 *
 * The embedding application owns transport bytes, authentication policy,
 * authorization policy, method dispatch, persistence, and recovery.
 * Rust owns version negotiation, frame validation, correlation tracking,
 * deadlines, cancellation observation, and outbound queueing.
 *
 * Build the Rust library with:
 *   cargo build -p syntra-ffi --features production
 */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SYNTRA_FFI_ABI_VERSION 1u
#define SYNTRA_FFI_OK 0
#define SYNTRA_FFI_INVALID (-1)
#define SYNTRA_FFI_CLOSED (-2)
#define SYNTRA_FFI_ABI_MISMATCH (-3)
#define SYNTRA_FFI_NOMEM (-4)
#define SYNTRA_FFI_EXPIRED (-5)
#define SYNTRA_FFI_INTERNAL (-6)

/* Opaque handles. Open exactly once, close exactly once. */
typedef struct syntra_ffi_client syntra_ffi_client_t;
typedef struct syntra_ffi_host syntra_ffi_host_t;

uint32_t syntra_ffi_abi_version(void);
void syntra_ffi_free(uint8_t *ptr, uintptr_t len);

/* Initiator core. */
int32_t syntra_ffi_client_open(uint32_t min_version, uint32_t max_version,
    const uint8_t *credential, uintptr_t credential_len,
    uint32_t default_timeout_ms, uint32_t max_concurrent,
    syntra_ffi_client_t **out);
int32_t syntra_ffi_client_hello_frame(syntra_ffi_client_t *c,
    uint8_t **out, uintptr_t *out_len);
int32_t syntra_ffi_client_activate(syntra_ffi_client_t *c,
    const uint8_t *ready_frame, uintptr_t len);
int32_t syntra_ffi_client_on_frame(syntra_ffi_client_t *c,
    const uint8_t *frame, uintptr_t len,
    uint64_t *terminal_ids, uintptr_t terminal_cap, uintptr_t *terminal_n,
    int32_t *notifications);
int32_t syntra_ffi_client_begin_call(syntra_ffi_client_t *c, uint64_t request_id,
    const uint8_t *method, uintptr_t method_len,
    const uint8_t *payload, uintptr_t payload_len, uint32_t timeout_ms,
    uint8_t **out_req_frame, uintptr_t *out_len);
int32_t syntra_ffi_client_cancel(syntra_ffi_client_t *c, uint64_t request_id,
    uint8_t **out_cancel_frame, uintptr_t *out_len);
int32_t syntra_ffi_client_take_outcome(syntra_ffi_client_t *c, uint64_t request_id,
    uint8_t **out, uintptr_t *out_len, int32_t *present);
int32_t syntra_ffi_client_poll_notification(syntra_ffi_client_t *c,
    uint8_t **out, uintptr_t *out_len, int32_t *present);
int32_t syntra_ffi_client_reap_expired(syntra_ffi_client_t *c,
    uint64_t *ids, uintptr_t cap, uintptr_t *n);
int32_t syntra_ffi_client_close(syntra_ffi_client_t *c);

/* Responder core. Dispatch lives in the embedding application. */
int32_t syntra_ffi_host_open(uint32_t min_version, uint32_t max_version,
    uint32_t max_concurrent, syntra_ffi_host_t **out);
int32_t syntra_ffi_host_accept_hello(syntra_ffi_host_t *h,
    const uint8_t *frame, uintptr_t len, uint32_t *version_out);
int32_t syntra_ffi_host_auth_complete(syntra_ffi_host_t *h,
    const char *principal, uintptr_t principal_len,
    uint8_t **out_ready_frame, uintptr_t *out_len);
int32_t syntra_ffi_host_on_frame(syntra_ffi_host_t *h,
    const uint8_t *frame, uintptr_t len,
    uint8_t **out_response, uintptr_t *out_len, int32_t *has_response,
    uint64_t *cancel_ids, uintptr_t cancel_cap, uintptr_t *cancel_n);
int32_t syntra_ffi_host_take_pending(syntra_ffi_host_t *h,
    uint64_t *request_id_out, uint8_t **out_req_frame, uintptr_t *out_len,
    int32_t *present);
int32_t syntra_ffi_host_is_cancelled(syntra_ffi_host_t *h, uint64_t request_id,
    int32_t *cancelled);
int32_t syntra_ffi_host_version(syntra_ffi_host_t *h, uint32_t *version_out);
int32_t syntra_ffi_host_answer(syntra_ffi_host_t *h,
    const uint8_t *result_frame, uintptr_t len, int32_t *expired);
int32_t syntra_ffi_host_notify(syntra_ffi_host_t *h,
    const uint8_t *payload, uintptr_t len);
int32_t syntra_ffi_host_next_outbound(syntra_ffi_host_t *h,
    uint8_t **out, uintptr_t *out_len, int32_t *present);
int32_t syntra_ffi_host_reap_expired(syntra_ffi_host_t *h,
    uint64_t *ids, uintptr_t cap, uintptr_t *n);
int32_t syntra_ffi_host_close(syntra_ffi_host_t *h);

#ifdef __cplusplus
}
#endif
#endif
