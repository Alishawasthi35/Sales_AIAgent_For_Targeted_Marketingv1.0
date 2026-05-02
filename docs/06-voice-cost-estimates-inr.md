# Voice call cost estimates (INR per minute)

Planning figures for **one connected minute** of a sales call using this stack: **Twilio** (outbound + Media Streams) and **Sarvam** (streaming STT, Bulbul v3 TTS, Sarvam-30B LLM). Rates are from vendor-published pages; confirm in your Twilio/Sarvam consoles before budgeting.

**FX:** examples use **₹85 per USD** for Twilio; use your effective rate when converting.

**Sources (checked at authoring):**

- Sarvam: [API Pricing](https://www.sarvam.ai/api-pricing)
- Twilio (India): [Programmable Voice Pricing — India](https://www.twilio.com/en-us/voice/pricing/in)

---

## Twilio (India destination, pay-as-you-go)

| Component | USD / min | ≈ INR @ ₹85/USD |
|-----------|-----------|------------------|
| Outbound → India **mobile** | $0.0405 | ~₹3.44 |
| Outbound → India **local / major cities** | $0.0497 | ~₹4.22 |
| **Media Streams** (WebSocket audio to your app) | $0.0040 | ~₹0.34 |

**Subtotal (outbound + Media Stream):**

- To **mobile:** ~₹3.44 + ₹0.34 ≈ **₹3.8/min**
- To **local / major cities:** ~₹4.22 + ₹0.34 ≈ **₹4.6/min**

**Caveat:** The India page applies to **India routings** on Twilio’s table. If your Twilio number is **hosted in another country** and you dial India, use the **origination → destination** price from Twilio (console or [Outbound Voice Pricing CSV](https://assets.cdn.prod.twilio.com/pricing-csv/OutboundVoicePricing.csv)).

**Not included:** monthly phone number rental, Answering Machine Detection (~$0.0075/call), recording, Voice Insights, taxes, or volume/committed discounts.

---

## Sarvam (typical usage for this repo)

From published pay-per-use API pricing:

| API | Published rate | Per connected minute (assumption) |
|-----|----------------|-------------------------------------|
| **STT** (Saaras, etc.) | ₹30 / hour of audio | ~**₹0.50/min** if ~1 minute of streamed caller audio per connected minute (rounded per second). |
| **TTS** (Bulbul **v3**) | ₹30 / 10k characters | Depends on bot talk time. Aligns with `tools/unit_economics.py` defaults (~45% agent talk, ~850 chars/min spoken): **~(0.45 × 850 / 10_000) × 30 ≈ ₹1.15/min**. Longer/faster replies increase this. |
| **LLM** (Sarvam-30B) | ₹2.5 / 1M input, ₹10 / 1M output tokens | Usually **small per minute** for short turns; can rise with long context and many turns. |

**Sarvam subtotal (reasonable default):** about **₹1.7–2.0/min** (STT + TTS + modest LLM).

---

## Combined variable cost (order of magnitude)

| India destination | Twilio (incl. Media Stream) | + Sarvam (STT + TTS + modest LLM) | **Total (typical range)** |
|-------------------|-----------------------------|-----------------------------------|---------------------------|
| **Mobile** | ~₹3.8/min | ~₹1.7–2.0/min | **~₹5.5–5.8/min** |
| **Local / major cities** | ~₹4.6/min | ~₹1.7–2.0/min | **~₹6.3–6.6/min** |

---

## Related project files

- **`tools/unit_economics.py`** — editable scenario calculator (USD revenue/costs). Its default Twilio **outbound** rate is a generic placeholder (**$0.014/min**), which **does not** match India mobile/landline rates above; update `ProviderCosts` for Twilio when modeling India calls.

---

## Revision note

Replace this document’s numbers when vendors change pricing or when you lock in **actual** routes (number country, destination type, optional Media Stream / AMD / recording).
