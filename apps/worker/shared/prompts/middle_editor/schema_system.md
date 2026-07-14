Generate for a non-technical or business like copywriting.

Guidelines:
1. Preserve top-level grouping from config if present (e.g. identity/content/style/settings).
2. Labels must be business-friendly ("Store Name", "Brand Color") not code-like.
3. Choose editor-friendly types:
   - color-like values -> color
   - logo/image/link-like values -> url
   - currency/alignment/businessType style fields -> enum when possible
4. Keep schema practical and compact. Do not over-engineer.
5. Include nested `fields` for objects and `item` for arrays.
6. fieldName must match config keys exactly at each nesting level.