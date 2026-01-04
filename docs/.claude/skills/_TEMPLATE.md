---
skill: SKILL_NAME
version: 1.0.0
domain: DOMAIN
primary_files:
  - path/to/file1.ts
  - path/to/file2.ts
total_loc: 0
dependencies:
  - other-skill-1
keywords:
  - keyword1
  - keyword2
  - keyword3
last_audit: 2025-12-10
quality_score: 0.0/10
---

# SKILL_NAME - Comprehensive Skill

**Version:** 1.0.0 (December 2025)
**Domain:** DOMAIN
**Total Lines:** X,XXX

---

## Quick Reference

[One paragraph, 50 words MAX. What is this system? What does it do? When would you use it?]

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      SYSTEM NAME                                 │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Component A                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │ Subcomponent│      │ Subcomponent│      │ Subcomponent│     │
│  │      A      │      │      B      │      │      C      │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Files Index

| File | Lines | Purpose |
|------|-------|---------|
| `path/to/MainFile.ts` | XXX | Main entry point |
| `path/to/TypesFile.ts` | XXX | Type definitions |
| `path/to/UtilsFile.ts` | XXX | Utility functions |

---

## API Reference

### MainClass

```typescript
// path/to/MainFile.ts:LINE

class MainClass {
  constructor(options: Options);
  method1(param: Type): ReturnType;
  method2(param: Type): ReturnType;
}
```

### Key Functions

```typescript
// path/to/file.ts:LINE
function keyFunction(param: Type): ReturnType;

// path/to/file.ts:LINE
function anotherFunction(param: Type): ReturnType;
```

### Types

```typescript
// path/to/types.ts:LINE

interface MainInterface {
  property1: Type;
  property2: Type;
}

type MainType = 'option1' | 'option2' | 'option3';
```

---

## Integration Points

### Connects To

| System | How | File |
|--------|-----|------|
| SystemA | Via EventBus | `path/to/integration.ts` |
| SystemB | Direct import | `path/to/consumer.ts` |

### Used By

| Consumer | Purpose |
|----------|---------|
| ComponentX | Feature description |
| ComponentY | Feature description |

---

## Common Patterns

### Pattern 1: Basic Usage

```typescript
import { MainClass } from '@/path/to/module';

const instance = new MainClass({ option: 'value' });
instance.method1(param);
```

### Pattern 2: With Configuration

```typescript
const config: Options = {
  option1: 'value1',
  option2: 'value2'
};
const instance = new MainClass(config);
```

### Pattern 3: Event Handling

```typescript
instance.on('event', (data) => {
  // Handle event
});
```

---

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option1` | `string` | `'default'` | Description |
| `option2` | `number` | `100` | Description |
| `option3` | `boolean` | `false` | Description |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_OPTION` | Description | `value` |

---

## Troubleshooting

### Error: "Error message here"

**Cause:** Description of what causes this error.

**Fix:**
```typescript
// Solution code
```

### Error: "Another error message"

**Cause:** Description of cause.

**Fix:** Step-by-step resolution.

### Common Mistakes

1. **Mistake 1:** Description and how to avoid.
2. **Mistake 2:** Description and how to avoid.
3. **Mistake 3:** Description and how to avoid.

---

## Testing

### Unit Tests

```bash
npm test -- path/to/tests/
```

### Integration Tests

```bash
npm run test:integration -- path/to/integration.test.ts
```

### Manual Verification

1. Step one
2. Step two
3. Expected result

---

## Key Commits

| Commit | Description |
|--------|-------------|
| `abc123def` | Initial implementation |
| `def456ghi` | Major feature addition |
| `ghi789jkl` | Bug fix for X |

---

## Related Skills

- [related-skill-1](../related-skill-1/README.md) - How they relate
- [related-skill-2](../related-skill-2/README.md) - How they relate

---

## Maintainer Notes

1. **Critical:** Important warning or constraint
2. **Pattern:** Recommended approach for X
3. **History:** Why something is done a certain way
4. **Future:** Planned changes or deprecations

---

## File Owners

| File Pattern | Owner |
|--------------|-------|
| `path/to/*.ts` | @owner |

---

**Last Updated:** 2025-12-10
**Quality Score:** X.X/10
