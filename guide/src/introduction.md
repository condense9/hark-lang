# Introduction

The goal of C9 is to generate infrastructure-as-code and glue logic to allow you
to express complex serverless computation.

"Complex serverless computation" is vaguely defined to mean computation in the
cloud that involves more than one "unit" of logic, i.e., function. These
functions may call each other, may run concurrently, and may need to be
synchronised to provide a result somewhere.

C9 is not a good choice (at the moment) for general purpose simple APIs. There's
too much overhead in the glue logic.

However, if you're frustrated with AWS Step Functions, or building data
pipelines manually, this is perfect.
