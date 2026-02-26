# CHANGELOG

<!-- version list -->

## v1.1.0 (2026-02-26)

### Bug Fixes

- **release**: Sync PLUGIN_VERSION and add it to semantic-release
  ([`cbbb6e1`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/cbbb6e156b2e086f5ef431d01c576cd58810f2b5))

- **smoke**: Update expected tool count to 27
  ([`f06817d`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/f06817d96fd1a3033dd2bed89d92a3c38f54e855))

- **smoke**: Update expected tool count to 28
  ([`ab24096`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/ab24096382a521ff50dd2cf18a35bc7409bdc009))

### Chores

- **deps**: Bump pre-commit hooks (ruff 0.15.4, cspell 9.7.0)
  ([`42d5fb5`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/42d5fb5b5678f3d0af4156edba62934d4d3a8740))

- **dev**: Add html and lcov coverage reports
  ([`d418b64`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/d418b64eab398af8c2dd4f5135b88ebbabe744ea))

- **lint**: Ignore RUF067 and RUF069 preview rules
  ([`a5fae63`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/a5fae633bc1224382f52377d6760db4df15bbe92))

- **stubs**: Align mypy stubs with field projection ORM usage
  ([`58be461`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/58be461f9c90522e373e8e32e40a2c5670d3c62d))

- **tests**: Split test_tools.py into per-domain files
  ([`c5101b3`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/c5101b3026cde95496a803331dfd6332d2eb0ca6))

### Features

- **tools**: Add field projection and ORM optimization across all tools
  ([`92b61c4`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/92b61c405d8c75ceb746b38a54f96202859f8918))

- **tools**: Add stock_by_category_and_location combinatory tool
  ([`dd09672`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/dd09672e8585b74109fa4cb6514ff4dd520d5cdc))

- **tools**: Add transport timeout and stock_pivot tool
  ([`2ff4688`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/2ff46881c8bfa44d6a304ca8faf885318c188bf3))

- **tools**: Expose total_stock field in list_parts
  ([`697de02`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/697de02e0ae3e3f7cac6d2c2487f3b81032d99f9))

- **tools**: Single-query recursive tree for categories and locations
  ([`1f01eb5`](https://github.com/eljefedelrodeodeljefe/inventree-mcp-plugin/commit/1f01eb5255a9d7894cf70bf257ca49353b65c7de))


## v1.0.0 (2026-02-26)

- Initial Release
