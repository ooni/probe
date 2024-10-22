---
name: Routine sprint releases
about: Monthly releases of probe-cli, etc.
title: ''
labels: priority/medium
assignees: DecFox

---

## Release information

Fill out this information for each release:

**Version Number:**

**Expected Release date:**

**Summary of changes:**

**Link to latest nightly:** 

## Pre-release communication 

- [ ] Post this message in the #ooni-probe-releases slack channel:

>@here 🏎️  OONI Probe Engine v[VERSION_NUMBER] release work has begun<br/>
Expected release date: [INSERT DATE] + or -  x days<br/>
Summary of changes: [INSERT LINK TO PR or CHANGESET]<br/>
Tracking issue: [INSERT LINK TO ISSUE]

## Release checklist

For extended documentation about the process, see [probe-cli's releasing.md](https://github.com/ooni/probe-cli/blob/master/docs/releasing.md).

### Psiphon

- [ ] probe-cli: pin to the latest [staging-client commit](https://github.com/Psiphon-Labs/psiphon-tunnel-core/tree/staging-client) using `./script/go.bash get -u -v`
- [ ] probe-cli: make sure `./script/go.bash list -json ./cmd/ooniprobe` does not include any pinned package in psiphon's `go.mod` or otherwise ask Psiphon developers whether this is fine

### Go version

- [ ] oocrypto: merge with upstream if needed
- [ ] oohttp: merge with upstream if needed
- [ ] probe-cli: possibly update `.github/workflows/gobash.yml`
- [ ] probe-cli: update the `GOVERSION` file if needed
- [ ] probe-cli: update the `toolchain` line inside of `go.mod`
- [ ] probe-cli: update the Go version mentioned in the `Readme.md` file
- [ ] probe-cli: update version specified in TH's Makefile

### Android

- [ ] probe-cli: update `NDKVERSION`, and `MOBILE/android/ensure` if needed

### Dependencies other than Psiphon

- [ ] probe-cli: ensure no dependency bumped its major version number using https://github.com/icholy/gomajor
- [ ] probe-cli: update dependencies with `./script/go.bash get -u -v -d ./...`
- [ ] probe-cli: update C dependencies

### Updating assets and definitions

- [ ] probe-cli: run `./script/updateminipipeline.bash`
- [ ] probe-cli: update github.com/ooni/probe-assets dependency
- [ ] probe-cli: update bundled certs (using `./script/go.bash generate ./...`)
- [ ] probe-cli: update user-agent at `internal/model/http.go`

### Maintenance

- [ ] probe-cli: sync stunreachability targets with snowflake (see `./internal/stuninput`)
- [ ] probe-cli: take a look at [go report card](https://goreportcard.com/report/github.com/ooni/probe-cli/v3)
- [ ] probe-cli: address any outstanding TODO in the diff since last release (or create an issue for it)
- [ ] probe-cli: try to address all the issues marked as "releaseBlocker"
- [ ] all: check whether to update the release documentation

### QA and alpha releasing

- [ ] probe-cli: check warnings emitted by `gosec` runs
- [ ] probe-cli: `./script/go.bash test -race -count 1 ./...` must pass locally
- [ ] probe-cli: tag an alpha release
- [ ] probe-cli: create the release/X.Y branch
- [ ] probe-cli: make sure all workflows are green in the release/X.Y branch
- [ ] team: communicate availability of an alpha release

### Releasing proper

- [ ] probe-cli: update `internal/version/version.go` in release/X.Y to be a stable release
- [ ] probe-cli: tag a new stable version in the release/X.Y branch
- [ ] probe-cli: update internal/version/version.go in master branch to be the next alpha

### Publishing stable packages

- [ ] probe-engine: run `./script/autoexport.bash`
- [ ] debian: publish packages
- [ ] android: publish packages
- [ ] oohelperd: publish docker container

## Post-release communication 

- [ ] iThena: notify about new release
- [ ] Update the `#ooni-probe-releases` slack channel:

> @here 🚀 🏎️ OONI Probe Engine v[VERSION_NUMBER] has been released.
