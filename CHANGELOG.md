# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [unreleased]

## [0.3.0] (2020-06-27)

### New

- New syntax for lists and hash maps (dictionaries)
- Optional API Gateway trigger for sessions
- Teal Tracebacks on error

### Changed

- More tests
- Massively improved CLI experience (colours, logs, progress indications)
- Activation Records used internally for stack management
- Big upgrades to underlying data model - more efficient and maintainable
- Removed the project name in config - it doesn't help anything, and adds extra
  state to keep track of (deployment ID is enough).
- Local run prints result at the end
- Local run prints stdout in real-time, instead in one go at the end
- No dependency on TL_REGION - just use AWS_DEFAULT_REGION
- Many other small improvements

### Fixed

- Tail-call optimisation bug which caused all values in a block to be kept
- *Lots* of other bugs.


## [0.2.4] (2020-06-08)

### Fixed

- Version tag naming in release.sh
- Writing `__version__` before release

## [0.2.3] (2020-06-08)

No changes - releasing just so that master is tagged.


## [0.2.2] (2020-06-08)

### Added

- Fractals example
- Tail-call optimisation for recusive function calls
- `teal deploy` and `teal destroy` for infrastructure management
- CLI interface for invoking sessions and getting session data
- `parse_float` builtin (string to float)
- service configuration file
- `nth` builtin (list access - maybe should be called `elem`)
- `wait` builtin to do what `await` does
- goto/loop at the compiler level

### Fixed

- Parser conflict with anonymous functions
- Various list data type instruction bugs
- Catch more runtime errors in AWS and record them

### Changed

- Teal names can start with underscore


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


[unreleased]: https://github.com/condense9/teal-lang/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/condense9/teal-lang/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/condense9/teal-lang/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/condense9/teal-lang/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/condense9/teal-lang/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/condense9/teal-lang/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/condense9/teal-lang/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/condense9/teal-lang/releases/tag/v0.1.0
