export const ciErrors = [
  "TypeError: Cannot read properties of undefined (reading 'currency')",
  "Module not found: Can't resolve '@acme/ui/Button'",
  'AssertionError: expected 10.05 to equal 10.04',
  'error TS2345: Argument of type string | undefined is not assignable',
  'npm ERR! ERESOLVE unable to resolve dependency tree',
  'Timeout: test_reindex exceeded 30000ms',
  'ESLint: 14 problems (14 errors) no-unused-vars',
  'Error: Unsupported argument "acl" in aws_s3_bucket',
  'ImportError: cannot import name "soft_unicode" from markupsafe',
  'docker: failed to compute cache key: "/app/dist" not found',
];

export const ciFixes = [
  'Guarded optional price in formatTotal · PR #1907 · 41s',
  'Updated import to @acme/ui/button · PR #884 · 1m 12s',
  'Pinned ROUND_HALF_EVEN in money.py · PR #1911 · 52s',
  'Narrowed userId before passing to fetchUser · PR #2033 · 38s',
  'Aligned react-dom peer to 18.3.1 · PR #412 · 1m 40s',
  'Raised reindex timeout, batched writes · PR #341 · 2m 04s',
  'Removed 14 unused imports · PR #562 · 33s',
  'Moved acl to aws_s3_bucket_acl resource · blocked for review',
  'Pinned markupsafe 2.0.1 in requirements · PR #219 · 47s',
  'Added build step before COPY dist · PR #97 · 1m 05s',
];