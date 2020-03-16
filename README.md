## C9C :: Condense9 Compiler

The instruction set, compiler and reference implementation of the abstract
machine.

Goal:
- write concurrent programs and have them execute on serverless infrastructure

How:
- automate the plumbing (passing data between functions, synchronisation of
  threads, etc)

What this is:
- an abstract imperative machine with native concurrency, and other
  cloud/serverless features*
- a high-level language to express concurrent computation, and other
  cloud/serverless features*
- a compiler

Sort of like programming a cluster, but without the cluster part.

*: Other features like specifying performance/placement constraints, and
creating event handlers (e.g. this is a GET handler, and must respond within
20ms)


### MVP Requirements

Build, deploy and run "data workflow" applications.

Infrastructure generation:
- lambda functions (and packages)
- ECS tasks
- SNS/SQS
- Bonus: API Gateway endpoints?!?!


### Development rules

If it doesn't have a test, it doesn't exist.

If the tests don't pass, don't merge it.

If it's in scratch, it doesn't exist.

Format Python with [Black](https://pypi.org/project/black/).

Run [Shellcheck](https://www.shellcheck.net/) over shell scripts.

Use Python 3.8.

#### The Oath

[Uncle Bob](https://blog.cleancoder.com/uncle-bob/2015/11/18/TheProgrammersOath.html)

I Promise that, to the best of my ability and judgement:

- I will not produce harmful code.

- The code that I produce will always be my best work. I will not knowingly
  allow code that is defective either in behavior or structure to accumulate.

- I will produce, with each release, a quick, sure, and repeatable proof that
  every element of the code works as it should.

- I will make frequent, small, releases so that I do not impede the progress of
  others.

- I will fearlessly and relentlessly improve my creations at every opportunity.
  I will never degrade them.

- I will do all that I can to keep the productivity of myself, and others, as
  high as possible. I will do nothing that decreases that productivity.

- I will continuously ensure that others can cover for me, and that I can cover
  for them.

- I will produce estimates that are honest both in magnitude and precision. I
  will not make promises without certainty.

- I will never stop learning and improving my craft.
