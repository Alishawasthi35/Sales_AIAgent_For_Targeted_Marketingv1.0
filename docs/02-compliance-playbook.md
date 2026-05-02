# Compliance and Risk Playbook

This playbook is operational guidance for a pilot, not legal advice. Before running paid outbound marketing campaigns in the US or other regulated markets, review the workflow with qualified counsel.

## Compliance Position

The product should only dial leads where the client can document a lawful contact basis. For marketing calls using an AI-generated or synthetic voice, treat the call as high-risk and require explicit consent language whenever possible.

Default rule:

> No consent record, no marketing call.

## Approved Lead Sources

Approved for MVP:

- Inbound forms with clear consent to be contacted by phone.
- Recent ad leads where the lead submitted their phone number for follow-up.
- Existing customers or prior inquiries where the client has a documented business relationship.
- Event, webinar, or demo signups with phone follow-up consent.
- Referral leads only if the referred person independently consented or requested contact.

Rejected for MVP:

- Scraped phone lists.
- Purchased cold lists without consent evidence.
- Old CRM records with unknown source.
- Leads marked as do-not-call or unsubscribed.
- Sensitive categories such as healthcare treatment, debt collection, political persuasion, credit repair, financial products, or legal claims.

## Required Lead Fields

Every dialable lead must include:

- `phone_number`
- `full_name`
- `lead_source`
- `consent_status`
- `consent_timestamp`
- `consent_text_or_url`
- `timezone_or_region`
- `client_id`
- `campaign_id`

Recommended fields:

- `source_record_id`
- `product_interest`
- `last_contacted_at`
- `preferred_callback_time`
- `notes`

## Consent Review Checklist

Before approving a campaign:

- Confirm how the lead list was collected.
- Confirm the client owns or is authorized to contact the leads.
- Confirm consent language allows phone follow-up for marketing or sales.
- Confirm whether AI-generated calls are explicitly mentioned. If not, classify the campaign as higher risk.
- Confirm leads are recent enough for the campaign purpose.
- Confirm the client can provide proof for sampled records.
- Confirm opt-out language and internal suppression process.

Campaigns that fail this checklist should be blocked until the client fixes the lead source or scope.

## Calling Window Policy

Default US-style calling window:

- Dial only between 9:00 AM and 7:00 PM recipient local time.
- Never dial before 8:00 AM or after 9:00 PM recipient local time.
- Avoid Sundays and local holidays during the pilot unless the client has a strong business reason.
- Retry no more than 3 times per lead in 7 days.

The system should derive local time from timezone, postal code, area code, or client-provided region. If local time cannot be determined, the lead should not be dialed automatically.

## Opening Script Requirements

Every call should identify:

- The client business name.
- The reason for the call.
- The lead source if useful.
- A simple opt-out path.
- AI disclosure where legally required or where the client chooses a conservative posture.

Conservative opening example:

> Hi, this is an AI assistant calling on behalf of GreenPeak Solar about the quote request you submitted. Is now a good time for a quick follow-up?

Opt-out example:

> If you do not want follow-up calls, just say "do not call" and I will mark that immediately.

## Opt-Out Handling

The agent must recognize and honor:

- "Do not call me."
- "Remove me."
- "Stop calling."
- "Take me off your list."
- "I am not interested, don't contact me again."

Required system behavior:

- End the call politely.
- Mark the phone number as suppressed immediately.
- Store `opted_out_at`, transcript evidence, campaign ID, and client ID.
- Block future calls across all campaigns for that client.
- Review whether the number should be globally suppressed across the platform.

Agent response:

> Understood. I will mark you as do-not-call. Sorry for the interruption.

## DNC and Suppression Workflow

MVP workflow:

- Maintain an internal suppression list from day one.
- Require clients to upload their internal DNC list before each campaign.
- Scrub campaign leads against client suppression lists before dialing.
- For US marketing campaigns, budget for National DNC and state-level list scrubbing before scaling beyond design partners.
- Keep a campaign audit log showing when scrubbing happened and how many leads were removed.

Suppression match policy:

- Normalize phone numbers to E.164.
- Match on phone number, not name.
- Do not allow campaign operators to override do-not-call status without admin review.

## Recording and Transcript Policy

Default pilot policy:

- Store transcripts for all calls.
- Store recordings only when the client confirms recording legality and business need.
- Show recording status in campaign configuration.
- Include recording disclosure if required by the jurisdiction.
- Retain transcripts and call metadata for at least 24 months during pilot unless counsel recommends a different policy.

Sensitive data policy:

- The agent should not request payment card data, SSNs, government IDs, medical data, passwords, or full addresses unless necessary for appointment routing.
- If a prospect shares sensitive data, redact it in summaries where possible.

## Campaign Approval Gate

Before a campaign can go live, require approval for:

- Lead source and consent sample.
- Script and offer.
- Caller ID and business identity.
- AI disclosure setting.
- Recording setting.
- Retry schedule.
- Calling window.
- Opt-out phrase handling.
- Human handoff number or booking link.

## Live Risk Controls

Automatic pause triggers:

- Complaint rate above 0.5% of connected calls.
- Opt-out rate above 5% of connected calls.
- Repeated wrong-number reports.
- Client uploads leads without consent fields.
- Agent produces unapproved claims.
- Call latency causes repeated failed conversations.

Manual controls:

- Campaign kill switch.
- Per-client daily call cap.
- Per-campaign throttle.
- Human review queue for low-confidence calls.
- Post-call script-adherence sampling.

## Client Contract Requirements

The client should warrant that:

- They have the right to contact uploaded leads.
- They will not upload scraped or non-consented marketing lists.
- They provided accurate consent and source metadata.
- They will honor opt-outs received from the platform.
- They approve the offer, claims, and script.
- They understand AI-assisted calls may be regulated differently by jurisdiction.

## Implementation Requirements

Minimum compliance data model:

- `lead.consent_status`
- `lead.consent_timestamp`
- `lead.consent_source`
- `lead.timezone`
- `lead.suppressed_at`
- `call.started_at`
- `call.ended_at`
- `call.local_time_at_dial`
- `call.outcome`
- `call.opt_out_detected`
- `campaign.approval_status`
- `campaign.ai_disclosure_mode`
- `campaign.recording_mode`
- `audit_log.actor`
- `audit_log.action`

## Decision

The MVP should reject unknown-source cold lists, require consent metadata, enforce calling windows, capture opt-outs immediately, and include a manual campaign approval gate before any dialing starts.
