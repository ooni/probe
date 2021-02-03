---
name: Routine sprint releases
about: Bi-weekly releases of probe-cli, etc.
title: ''
labels: effort/M, priority/medium
assignees: bassosimone

---

- [ ] psiphon: run ./update.bash
- [ ] probe-cli: update dependencies
- [ ] probe-cli: update internal/engine/httpheader/useragent.go
- [ ] probe-cli: update internal/engine/version/version.go
- [ ] probe-cli: update cmd/ooniprobe/internal/version/version.go
- [ ] probe-cli: update internal/engine/resources/assets.go
- [ ] probe-cli: update bundled certs (using `go generate ./...`)
- [ ] probe-cli: make sure all workflows are green
- [ ] probe-cli: tag a new version
- [ ] probe-cli: update internal/engine/version/version.go to be alpha
- [ ] probe-cli: update cmd/ooniprobe/internal/version/version.go to be alpha
- [ ] probe-cli: create release at GitHub
- [ ] probe-cli: update mobile-staging branch to create oonimkall
- [ ] probe-android: pin to latest oonimkall
- [ ] probe-ios: pin to latest oonimkall
- [ ] probe-desktop: pin to latest cli
- [ ] probe: create issue for next routine release
- [ ] e2etesting: see whether we can remove legacy checks
