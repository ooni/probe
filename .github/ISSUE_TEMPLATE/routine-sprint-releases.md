---
name: Routine sprint releases
about: Bi-weekly releases of probe-cli, etc.
title: ''
labels: effort/M, priority/medium
assignees: bassosimone

---
- [ ] psiphon: run ./update.bash
- [ ] ooni/go: merge with upstream if needed
- [ ] oohttp: merge with upstream if needed
- [ ] ooni/go-libtor: update
- [ ] probe-cli: sync stunreachability targets with snowflake (see `./internal/stuninput`)
- [ ] probe-cli: update the version of go used by github actions
- [ ] probe-cli: take a look at [go report card](https://goreportcard.com/report/github.com/ooni/probe-cli)
- [ ] probe-cli: address any outstanding TODO in the diff since last release (or create an issue for it)
- [ ] probe-cli: ensure `./mk` is using latest version of several tools
- [ ] probe-cli: ensure github.com/bassosimone/monorepo is using the latest version of several tools
- [ ] probe-cli: update dependencies with `go get -u -v -d ./...`
- [ ] probe-cli: ensure no dependency bumped its major version number
- [ ] probe-cli: update internal/engine/httpheader/useragent.go
- [ ] probe-cli: update internal/version/version.go
- [ ] probe-cli: update github.com/ooni/probe-assets dependency
- [ ] probe-cli: update bundled certs (using `go generate ./...`)
- [ ] probe-cli: make sure all workflows are green
- [ ] probe-cli: `go test -race -count 1 ./...` must pass locally
- [ ] probe-cli: tag a new version
- [ ] probe-cli: update internal/version/version.go to be alpha
- [ ] probe-cli: create release at GitHub
- [ ] probe-android: pin to latest oonimkall
- [ ] probe-ios: pin to latest oonimkall
- [ ] probe-desktop: pin to latest cli
- [ ] probe: create issue for next routine release
- [ ] e2etesting: see whether we can remove legacy checks
