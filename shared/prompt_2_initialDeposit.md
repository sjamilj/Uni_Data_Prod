# Stage 2d — Initial deposit & tuition payment (LLM only)

Extract **only** `initialDeposit` and deposit-related `feesMetaData` from the course page and university deposit page.

Do **not** output `uniName`, course URL, academic `requirements`, IELTS/PTE/TOEFL, scholarships, intake, duration, or `applicationFee` — Python fills those.

Use only the provided input. Never use outside knowledge. Missing → `""` or `[]`.

## Input
- Course: `{COURSE_NAME}`
- URL: `{COURSE_URL}`
- **International tuition fee (use for percentage calculations):** `{TUITION_FEE}`
- Stage 1 JSON (course-page fee facts — tuition fee reference):

```json
{STAGE1_JSON}
```

- Course page (fees / funding sections):

```
{COURSE_CONTENT}
```

- University deposit / how-to-pay page only:

```
{DEPOSIT_CONTENT}
```

## Rules

### 1. `initialDeposit` (top-level field)
- `initialDeposit` MUST be a top-level field, **outside** `feesMetaData`.
- **Ignore** any `initialDeposit` value in Stage 1 JSON — it may be wrong. Extract deposit only from the **course page** and **deposit page**.
- If the source explicitly gives a deposit amount, use that exact amount.
- Example: `£4,000 deposit` → `"initialDeposit": "£4,000"`
- Do **not** recalculate an explicitly stated deposit amount.

### 2. Percentage deposit
- If the source gives a deposit as a **percentage** and no exact amount is stated, calculate:

  `Deposit = International tuition fee × Percentage ÷ 100`

- Example: International tuition fee = `£20,000`, Deposit = `50%` → `"initialDeposit": "£10,000"`
- Use `{TUITION_FEE}` / Stage 1 `tuitionFee` as the international fee when calculating.

### 3. International student priority
- If multiple tuition fees are provided, **always** use the **international student** tuition fee for percentage calculations.
- Do **not** use the UK/Home tuition fee for an international student calculation.

Example:

- UK tuition fee = `£10,000`
- International tuition fee = `£20,000`
- Deposit = `50%`

→ `"initialDeposit": "£10,000"`

### 4. International-specific percentage
- If the source gives different deposit percentages for UK/Home and International students, use the **International** percentage with the **International** tuition fee.

Example:

- UK deposit = `20%`
- International deposit = `50%`
- International tuition fee = `£20,000`

→ `"initialDeposit": "£10,000"`

### 5. If international tuition fee is missing
- Do **not** use the UK/Home tuition fee as a substitute.
- If the applicable international tuition fee cannot be identified, use `"initialDeposit": ""`.

### 6. `feesMetaData`
- Put payment details from the source inside `feesMetaData`.
- Use a relevant `subtitle`, such as `"Initial tuition Deposit"`.
- Include payment schedules, percentages, instalments, registration payments, and payment months in `description`.
- Preserve source information accurately.
- Do **not** invent or infer information.

### 7. Strict rules
- Use only the provided sources and provided tuition fee.
- Do not guess. Do not invent amounts. Do not convert currencies.
- Do not change explicitly stated monetary amounts.
- Calculate only when a percentage **and** applicable international tuition fee are available.
- Return valid JSON only.

## Example

Tuition fees: UK = `£10,000`, International = `£20,000`

Source: *"International students must pay 50% of their tuition fee at registration and the remaining 50% in January."*

```json
{
  "initialDeposit": "£10,000",
  "feesMetaData": [
    {
      "subtitle": "Initial tuition Deposit",
      "description": [
        "International students must pay 50% of their tuition fee at registration and the remaining 50% in January."
      ]
    }
  ]
}
```

## Output

Return exactly one JSON object in a single ` ```json ` block. **Only these keys:**

```json
{
  "initialDeposit": "",
  "feesMetaData": []
}
```
