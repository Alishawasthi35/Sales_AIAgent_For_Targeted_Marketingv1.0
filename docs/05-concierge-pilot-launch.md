# Concierge Pilot Launch Kit

## Pilot Objective

Launch with 2-3 design partners and prove that the AI calling service can create qualified booked appointments from warm leads at a profitable gross margin and acceptable compliance risk.

The pilot should validate:

- Buyers will pay for the service.
- Leads can be called lawfully.
- The AI agent can hold short appointment-booking conversations.
- Campaign operations can be run manually before building self-serve features.
- Unit economics support a scalable pricing model.

## Design Partner Criteria

Accept a design partner only if they meet these conditions:

- They have at least 100 warm leads/month.
- Their average deal value is high enough to justify appointment booking.
- They can provide lead source and consent records.
- They have a human closer or sales rep ready for handoff.
- They can approve a script within 48 hours.
- They agree to weekly review calls during the pilot.
- They understand this is a controlled pilot, not an unlimited dialer.

Reject or defer clients that:

- Want to upload scraped cold lists.
- Cannot explain where leads came from.
- Demand aggressive or misleading scripts.
- Sell regulated or high-risk products without legal review.
- Cannot handle booked appointments quickly.

## Pilot Offer

Recommended design-partner commercial terms:

- $500-$750 setup fee.
- $300-$500 monthly platform fee.
- 1,000-2,000 connected minutes included.
- $0.18 per connected minute overage.
- Optional $25 per booked appointment after quality threshold is met.

Pilot duration:

- 30 days minimum.
- Extend to 60 days only if the first month has clean compliance and promising conversion data.

Pilot promise:

> We will help you contact warm leads faster, qualify them, and book more sales conversations. We will not guarantee closed revenue during the pilot.

## Onboarding Checklist

Client intake:

- Business name.
- Website.
- Industry.
- Main offer.
- Target customer.
- Service areas.
- Sales hours.
- Handoff phone number.
- Appointment booking link.
- Current lead sources.
- Current monthly lead volume.
- Current cost per booked appointment.
- Existing opt-out or DNC list.

Campaign setup:

- Upload sample leads.
- Verify required consent metadata.
- Confirm approved lead sources.
- Define one campaign goal.
- Draft call opening.
- Draft qualification questions.
- Draft objection responses.
- Define disallowed claims.
- Define booking or transfer rule.
- Choose recording mode.
- Choose AI disclosure mode.
- Approve retry schedule.
- Approve calling windows.

Pre-launch tests:

- Internal test call to founder/operator.
- Test wrong-number path.
- Test opt-out path.
- Test callback request.
- Test appointment booking.
- Test human transfer.
- Test voicemail handling.
- Review transcript summary quality.
- Review latency and audio quality.

## Pilot Operating Cadence

Daily during first week:

- Review all call outcomes.
- Listen to or inspect 10-20 sample transcripts.
- Check opt-outs and complaints.
- Check wrong-number reports.
- Check whether the agent made any unapproved claims.
- Update objection responses if needed.

Weekly:

- Send client a campaign summary.
- Review booked appointments and no-shows.
- Review cost per booked appointment.
- Decide whether to expand, pause, or revise the script.
- Update lead-source quality assumptions.

End of pilot:

- Compare baseline appointment rate against AI-assisted rate.
- Calculate gross margin.
- Summarize compliance incidents.
- Decide whether to convert to monthly plan.
- Collect testimonial or case study if successful.

## Launch Sequence

Day 0-2: Sales and qualification

- Interview the client.
- Confirm lead volume, lead source, and business value per appointment.
- Explain consent requirements and reject non-compliant lead sources.
- Agree on pilot pricing and outcome definition.

Day 3-5: Campaign build

- Import leads.
- Build script and objection tree.
- Configure compliance settings.
- Run internal test calls.
- Get written client approval.

Day 6-10: Soft launch

- Dial only 25-50 leads/day.
- Review every connected call transcript.
- Pause immediately on complaints or opt-out spikes.
- Tune script length and qualification questions.

Day 11-30: Controlled scale

- Increase to 100-250 leads/day only if quality is stable.
- Run weekly client reporting.
- Keep human review on a sample of calls.
- Avoid adding a second campaign until the first one is stable.

## Campaign Quality Scorecard

Green:

- Appointment/callback rate above 8% of connected conversations.
- Opt-out rate below 5%.
- Complaint rate below 0.5%.
- No unapproved claims found in transcript review.
- Average response latency below 1.5 seconds.

Yellow:

- Appointment/callback rate between 4-8%.
- Opt-out rate between 5-8%.
- Complaint rate between 0.5-1%.
- Repeated objections not handled well.
- Latency above 1.5 seconds but calls still complete.

Red:

- Unknown or weak lead consent.
- Appointment/callback rate below 4%.
- Opt-out rate above 8%.
- Complaint rate above 1%.
- Agent makes misleading claims.
- Client cannot service booked appointments.

Red campaigns should be paused until the cause is fixed.

## Client Weekly Report Template

Subject:

> Weekly AI calling pilot report: {campaign_name}

Body:

```text
Campaign: {campaign_name}
Period: {start_date} to {end_date}

Lead volume:
- Leads uploaded:
- Leads dialable after compliance checks:
- Calls attempted:
- Connected calls:

Outcomes:
- Booked appointments:
- Callback requested:
- Qualified but not booked:
- Not interested:
- Voicemail/no answer:
- Do-not-call:

Economics:
- Estimated connected minutes:
- Estimated platform cost:
- Cost per booked appointment:
- Client-estimated value per booked appointment:

Quality notes:
- Top objections:
- Script changes recommended:
- Compliance/risk flags:

Next actions:
- Client:
- Platform team:
```

## Internal Review Checklist

For each design partner:

- Did the client provide valid leads?
- Did the agent follow the approved script?
- Did prospects understand why they were called?
- Did opt-out handling work every time?
- Did booked appointments show up correctly?
- Did the client accept the lead quality?
- Did unit economics meet target margin?
- Did support load stay manageable?

## Expansion Criteria

Expand a pilot only if:

- Compliance review is clean.
- Gross margin is above 60%.
- Client wants to continue paying.
- Appointment quality is acceptable to the client.
- Operator time per campaign is trending down.
- The product team knows exactly what to automate next.

Do not expand because the system can technically place more calls. Expand only when the client outcome, compliance posture, and margin are all healthy.

## Next Build Priorities After Pilot

If the pilot succeeds:

- Automate CSV validation and consent checks.
- Build a client-facing campaign dashboard.
- Add CRM export for booked appointments.
- Add script A/B testing.
- Add provider cost comparison using Telnyx.
- Add a formal QA queue for risky calls.

If the pilot fails:

- Diagnose whether failure came from lead quality, script, AI latency, voice quality, offer weakness, or client follow-up.
- Do not build more self-serve UI until the failure cause is understood.
- Keep the core narrow and run another controlled pilot in a better-suited niche.

## Decision

Launch only as a concierge service with 2-3 design partners, daily human review, strict campaign approval, and a clear conversion target: booked appointments or qualified callbacks from consent-backed warm leads.
