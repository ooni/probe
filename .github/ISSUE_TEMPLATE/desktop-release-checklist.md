---
name: Desktop Release Checklist
about: 'Checklist for desktop releases '
title: 'Probe-desktop: Integrate engine v[VERSION_NUMBER]-rc.1 into probe-desktop
  v[VERSION_NUMBER]-rc.1'
labels: ''
assignees: majakomel

---

## Release information

Fill out this information for each release:

This issue is to track the work needed to integrate probe-engine v[VERSION_NUMBER]-rc.1 into probe-desktop

Engine version: v[VERSION_NUMBER]-rc.1 [LINK TO ENGINE CHANGESET]

Expected shipping date: [SPECIFY WHEN THIS IS EXPECTED TO BE RELEASED]

Additional specific changes: [INSERT ADDITIONAL CHANGES PART OF THIS RELEASE THAT ARE NOT PART OF ENGINE]

What to look out for while testing: [PROVIDE LIST OF THINGS A PERSON SHOULD TEST BEYOND TYPICAL QA CHECKLIST]

Instructions on how to test this release: [PROVIDE LINK TO DOCUMENTATION EXPLAINING HOW TO INSTALL THIS SPECIFIC VERSION ON YOUR DEVICE]

## Integration communication 

- [ ] Post this message in the #ooni-probe-releases slack channel when integration work is ready to begin:

>@here 📱💻 🔗 OONI Desktop integration work for OONI Probe Engine v[VERSION_NUMBER] will now begin.<br/>
Check this issue for details and progress: [INSERT LINK TO ISSUE]<br/>
We expect to finish this integration by: [INSERT DATE]<br/>

## Pre-release communication 

- [ ] One the integration with the Probe Engine has completed and we are ready to proceed to the next step, share this update in the #ooni-probe-releases slack channel:

> @here 📱💻 🛠️ OONI Desktop work towards a final release of OONI Probe Desktop v[VERSION_NUMBER] will now begin.<br/>
We expect to release this by [INSERT DATE]<br/>
Check this issue for details and progress: [INSERT LINK TO ISSUE]<br/>
We expect to finish this by: [INSERT DATE]<br/>

### Pre-release checklist

- [ ] Run through desktop QA checklist 

## Release progress communication 

- [ ] Once QA and pre-release process has been completed update the #ooni-probe-releases slack channel:

>@here ✅ 📱💻  OONI Probe Desktop v[VERSION_NUMBER] is ready to be released.
It will be released at [INSERT TIME AND DATE].
Check this issue for details and progress: [INSERT LINK TO ISSUE]<br/> 

## Post release communication 

- [ ] Release has been been completed update the #ooni-probe-releases slack channel:

>@here ✅ 📱💻  OONI Probe Desktop v[VERSION_NUMBER] has been released<br/>
Check this issue for details: [INSERT LINK TO ISSUE]<br/>
