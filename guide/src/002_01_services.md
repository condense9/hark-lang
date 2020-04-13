# Core Concepts

- Services
- Handlers
- Events
- Infrastructure
- Functions
- Compilation

**Services** are the central concept that tie everything together.

Services are comprised of a number of **Handlers**.

Handlers are C9 functions which are executed in response to an **Event**.

Events are very generally defined as anything that can happen at any time, and
they may have some data attached to them describing the Event. Examples of Events:

- An API call (data: the request parameters)
- An object is uploaded to an S3 bucket (data: the bucket name, the object key, ...**

**Infrastructure** is (an abstraction of) some cloud infrastructure or resource.
Examples:

- An object store (S3 bucket)
- A key-value store (AWS DynamoDB)

Infrastructure is translated into Infrastructure-as-Code by the C9 Synthesiser.

**Compiling a Handler** means generating the C9 Machine instructions to run that
handler, given some inputs on the stack.

**Compiling a Service** means compiling each of the Handlers, and then
Synthesising the whole service.

**Synthesis** means generating infrastructure-as-code *and deployment logic* for
the service.

Deployment logic includes packaging up all user code (e.g. into a Zip file for
deployment to Lambda).
