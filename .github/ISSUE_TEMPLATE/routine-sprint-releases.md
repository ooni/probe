---
name: Routine sprint releases
about: Bi-weekly releases of probe-cli, etc.
title: ''
labels: effort/M, priority/medium
assignees: bassosimone

---
- [ ] probe-cli: pin to the latest [staging-client commit](https://github.com/Psiphon-Labs/psiphon-tunnel-core/tree/staging-client) using `go get -u -v`
- [ ] probe-cli: make sure `go list -json ./cmd/ooniprobe` does not include any pinned package in psiphon's `go.mod`
- [ ] probe-cli: possibly update `.github/workflows/gobash.yml`
- [ ] probe-cli: update cdeps
- [ ] probe-cli: run `./script/updateminipipeline.bash`
- [ ] oocrypto: merge with upstream if needed
- [ ] oohttp: merge with upstream if needed
- [ ] probe-cli: sync stunreachability targets with snowflake (see `./internal/stuninput`)
- [ ] probe-cli: take a look at [go report card](https://goreportcard.com/report/github.com/ooni/probe-cli/v3)
- [ ] probe-cli: address any outstanding TODO in the diff since last release (or create an issue for it)
- [ ] probe-cli: update `GOVERSION` if needed
- [ ] probe-cli: update `NDKVERSION`, and `MOBILE/android/ensure` if needed
- [ ] probe-cli: update the Go version mentioned in the `Readme.md` file
- [ ] probe-cli: update dependencies with `go get -u -v -d ./...`
- [ ] probe-cli: ensure no dependency bumped its major version number using https://github.com/icholy/gomajor
- [ ] probe-cli: update user-agent at internal/model/http.go
- [ ] probe-cli: update internal/version/version.go
- [ ] probe-cli: try to address all the issues marked as "releaseBlocker"
- [ ] probe-cli: update github.com/ooni/probe-assets dependency
- [ ] probe-cli: update bundled certs (using `go generate ./...`)
- [ ] probe-cli: make sure all workflows are green
- [ ] probe-cli: check warnings emitted by `gosec` runs
- [ ] probe-cli: `go test -race -count 1 ./...` must pass locally
- [ ] probe-cli: tag a new version
- [ ] probe-cli: update internal/version/version.go to be alpha
- [ ] probe-engine: run ./script/autoexport.bash
- [ ] debian: publish packages
- [ ] android: publish packages
- [ ] probe: create issue for next routine release
- [ ] iThena: notify about new release
