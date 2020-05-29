# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [unreleased]


## [0.2.1] (2020-05-29)

### Fixed

- CLI bugs

### Added

- CLI colours and cleaner interface
- CONTRIBUTING.md document
- Better README info, and functions diagram

### Changed

- Simpler standard output model (just text). This may change again before the
  next release...
- Remove "Evaluator" class in the Machine. Much simpler now.


## [0.2.0] (2020-05-18)

Subtantial release - several changes not captured here.

### Added 

- Completely new syntax
- Add ability to import from the python builtin module 
- Env variable to enable/disable importing from builtin
- Env variable to configure Lambda timeout 
- Add ability to provide Teal code for just that session when calling the `new`
  awslambda endpoint, rather than using the "base session"
- awslambda API endpoints: set a single session executable,  get session output
- Add "expires_on" attribute for DynamoDB Session items, so that they can be
  deleted automatically (using DynamoDB TTL)
- A CHANGELOG.md
- Various other changes

### Fixed

- Return dict from the Lambda handlers, so that API Gateway integrations work
  correctly.


## [0.1.0] (2020-05-01)

Initial release.

### Added 

- Minimal first-draft Teal language and command-line tool
- Basic end-to-end tests
- A few examples


[unreleased]: https://github.com/condense9/teal-lang/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/condense9/teal-lang/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/condense9/teal-lang/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/condense9/teal-lang/releases/tag/v0.1.0
