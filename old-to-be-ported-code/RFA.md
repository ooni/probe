# Primary Criteria
## Enables

[X] Circumvention and/or community empowering communications technologies

## Impacts
### Describe the project's focus on making an impact, either for high value users (people in greater danger) or for large numbers of users.

OONI will impact mainly two distinct categories of users: those interested in doing
research on censorship and raising awareness on it, and those that are subject to censorship
and wish to understand how this is being performed at them.

We want to build a testing framework that will allow researchers to use the results
from default tests or write their own. Since the methodologies are public and the tools are
open source researchers will be able to properly understand the effectiveness of the
test and draw their own conclusions based on the data.

Normal citizens that are subject to censorship will be able to understand that they are being
censored and the pervasiveness of the censorship that they are subject to. The impact will be
greatly amplified by second order effects of OONI once independent sources will base their
visualization and reports on the OONI open data.

The skillful user will be able to verify that the analysis on censorship of his country is
true since the data that the analysis is based on is public.

Policy makers will also be able to look at analysis that reference raw OONI data when
making decisions on censorship.

## Support
### Describe project's known funding/support both direct/indirect cash or in-kind

Currently not directly funded. <FILL ME?>

# Secondary Criteria
## Demand
### Can demonstrate external demand (i.e., demand originated from potential users, not from would-be patrons of some possibly hypothetical set of users).

There exists a big community of activists and researchers that deal with censorship. These
people would be able to contextualize censorship related data without having to develop their
own tools.

The flexibility of the framework should allow them to implement their own tests when the
default set of tests does not suffice and work with us to have them deployed on the
machines running ooni-probe.

## Measurement
### Articulates a measurable set of evaluation criteria and milestone metrics

A good criteria could be of developing an X amount of questions related to
censorship that we want answered (e.x. is DNS filtering happening? is
squid HTTP proxy being used?) and work towards deploying these tests in a
Y amount of country.

Depening on the budget and time contraints we can determine the optimal
(and doable) values of X and Y and set N milestones for reaching numbers
X_i, Y_i < X, Y (i in (0, N)).

## Usability/Accessibility
### Demonstrates a high degree of usability/accessibility.

ooni-probe is written in python and is therefore cross-platform and deployable
anywhere there is a python interpreter.

It may also be a good idea to have this software integrated into a specific hardware
container (e.x. the TorRouter?).

The user running the ooni-probe tests should be aware of the consequences of running
such software on his machine (e.x. if you are in Syria maybe you could get into
trouble for running such software) and should be able to select only a subset of
less risky tests.


## Need
### Fills a potential need or function that is currently unfilled, rather than re-inventing the wheel

There are currently projects aimed at measuring censorship in one
way or another but they either use non open methodologies or their
tools are not open sources. OONI aims at filling this gap by
creating the first open source framework for developing network
tests and collecting data on censorship.

## Community
### Builds a collaborative open source community of developers (“bus factor higher than 1”).

There will be two main communities of developers comming out of OONI. One will be
that of OONI test writers and those developing the core framework.

We aim at getting as much people as possible to write tests specific to their
country and make this process as easy as possible, even for non skilful programmers.

Anybody interested in expanding the core of the system will be encouraged
and helped in making their first steps.

## Collaboration
### Facilitates inter-project collaboration, including: talking with others doing similar things and identifying potential points of overlap; acted/planned to modularize code to enable others to reuse (NOTE: doesn’t require over-design and/or real break up until there’s actually demand-driven need for a specific library).

We are in contact with people from the chokepoint project and
wish to keep this collaboration active. They are focussed on transforming
the data that will come out of ooni-probe and we can focus on building
the tools for enabling them to visualize and contextualize the data.

