module syntra-schema-tests

go 1.22

require (
	github.com/tinklehq/syntra/bindings/go v0.0.0
	google.golang.org/protobuf v1.36.6
)

// Replaced with smoke-test output generated into the ignored .tmp/ tree by
// scripts/validate-schema.py. Never committed; never a repository binding.
replace github.com/tinklehq/syntra/bindings/go => ../../../.tmp/bufgen/go
