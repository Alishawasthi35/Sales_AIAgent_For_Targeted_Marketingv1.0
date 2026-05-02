"""Pilot unit-economics calculator for the AI sales calling service.

Run:
    python tools/unit_economics.py
    python tools/unit_economics.py --provider telnyx --minutes 5000 --clients 3

All defaults are editable assumptions for planning, not vendor guarantees.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


INR_PER_USD = 85.0


@dataclass(frozen=True)
class ProviderCosts:
    name: str
    outbound_per_min: float
    media_stream_per_min: float
    amd_per_call: float
    recording_per_min: float
    monthly_number: float


@dataclass(frozen=True)
class SarvamCosts:
    stt_per_hour_inr: float = 30.0
    tts_per_10k_chars_inr: float = 30.0
    llm_input_per_1m_tokens_inr: float = 2.5
    llm_output_per_1m_tokens_inr: float = 10.0
    agent_talk_ratio: float = 0.45
    chars_per_spoken_minute: int = 850
    input_tokens_per_call: int = 1_000
    output_tokens_per_call: int = 350

    @property
    def stt_per_min_usd(self) -> float:
        return (self.stt_per_hour_inr / 60) / INR_PER_USD

    @property
    def tts_per_char_usd(self) -> float:
        return (self.tts_per_10k_chars_inr / 10_000) / INR_PER_USD

    def tts_cost(self, connected_minutes: float) -> float:
        spoken_chars = connected_minutes * self.agent_talk_ratio * self.chars_per_spoken_minute
        return spoken_chars * self.tts_per_char_usd

    def llm_cost(self, calls: int) -> float:
        input_cost = (
            calls
            * self.input_tokens_per_call
            * self.llm_input_per_1m_tokens_inr
            / 1_000_000
            / INR_PER_USD
        )
        output_cost = (
            calls
            * self.output_tokens_per_call
            * self.llm_output_per_1m_tokens_inr
            / 1_000_000
            / INR_PER_USD
        )
        return input_cost + output_cost


PROVIDERS = {
    "twilio": ProviderCosts(
        name="Twilio",
        outbound_per_min=0.0140,
        media_stream_per_min=0.0040,
        amd_per_call=0.0075,
        recording_per_min=0.0025,
        monthly_number=1.15,
    ),
    "telnyx": ProviderCosts(
        name="Telnyx",
        outbound_per_min=0.0070,
        media_stream_per_min=0.0035,
        amd_per_call=0.0020,
        recording_per_min=0.0020,
        monthly_number=1.00,
    ),
}


@dataclass(frozen=True)
class Scenario:
    provider: ProviderCosts
    connected_minutes: int
    average_call_minutes: float
    clients: int
    monthly_platform_fee: float
    setup_fee_per_client: float
    setup_fee_recognition_months: int
    usage_price_per_min: float
    booked_appointments: int
    success_fee: float
    fixed_monthly_cost: float
    use_amd: bool
    record_calls: bool

    @property
    def connected_calls(self) -> int:
        return max(1, round(self.connected_minutes / self.average_call_minutes))

    @property
    def recognized_setup_revenue(self) -> float:
        return self.clients * self.setup_fee_per_client / self.setup_fee_recognition_months

    @property
    def revenue(self) -> float:
        return (
            self.clients * self.monthly_platform_fee
            + self.recognized_setup_revenue
            + self.connected_minutes * self.usage_price_per_min
            + self.booked_appointments * self.success_fee
        )


def calculate(scenario: Scenario, sarvam: SarvamCosts) -> dict[str, float]:
    provider = scenario.provider
    minutes = scenario.connected_minutes
    calls = scenario.connected_calls

    telephony = minutes * provider.outbound_per_min
    media_streaming = minutes * provider.media_stream_per_min
    amd = calls * provider.amd_per_call if scenario.use_amd else 0.0
    recording = minutes * provider.recording_per_min if scenario.record_calls else 0.0
    phone_numbers = scenario.clients * provider.monthly_number

    stt = minutes * sarvam.stt_per_min_usd
    tts = sarvam.tts_cost(minutes)
    llm = sarvam.llm_cost(calls)

    variable_cost = telephony + media_streaming + amd + recording + stt + tts + llm
    total_cost = variable_cost + phone_numbers + scenario.fixed_monthly_cost
    gross_profit = scenario.revenue - total_cost
    gross_margin = gross_profit / scenario.revenue if scenario.revenue else 0.0

    return {
        "connected_calls": calls,
        "revenue": scenario.revenue,
        "telephony": telephony,
        "media_streaming": media_streaming,
        "amd": amd,
        "recording": recording,
        "phone_numbers": phone_numbers,
        "sarvam_stt": stt,
        "sarvam_tts": tts,
        "sarvam_llm": llm,
        "fixed_monthly_cost": scenario.fixed_monthly_cost,
        "variable_cost": variable_cost,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "cost_per_connected_minute": total_cost / minutes,
        "revenue_per_connected_minute": scenario.revenue / minutes,
    }


def money(value: float) -> str:
    return f"${value:,.2f}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def print_report(scenario: Scenario, results: dict[str, float]) -> None:
    print(f"Provider: {scenario.provider.name}")
    print(f"Connected minutes: {scenario.connected_minutes:,}")
    print(f"Estimated connected calls: {int(results['connected_calls']):,}")
    print()
    print("Revenue")
    print(f"  Monthly recurring/platform: {money(scenario.clients * scenario.monthly_platform_fee)}")
    print(f"  Recognized setup revenue:   {money(scenario.recognized_setup_revenue)}")
    print(f"  Usage revenue:              {money(scenario.connected_minutes * scenario.usage_price_per_min)}")
    print(f"  Success fee revenue:        {money(scenario.booked_appointments * scenario.success_fee)}")
    print(f"  Total revenue:              {money(results['revenue'])}")
    print()
    print("Costs")
    print(f"  Telephony:                  {money(results['telephony'])}")
    print(f"  Media streaming:            {money(results['media_streaming'])}")
    print(f"  Answering machine detect:   {money(results['amd'])}")
    print(f"  Recording:                  {money(results['recording'])}")
    print(f"  Phone numbers:              {money(results['phone_numbers'])}")
    print(f"  Sarvam STT:                 {money(results['sarvam_stt'])}")
    print(f"  Sarvam TTS:                 {money(results['sarvam_tts'])}")
    print(f"  Sarvam LLM:                 {money(results['sarvam_llm'])}")
    print(f"  Fixed monthly ops:          {money(results['fixed_monthly_cost'])}")
    print(f"  Total cost:                 {money(results['total_cost'])}")
    print()
    print("Unit Economics")
    print(f"  Gross profit:               {money(results['gross_profit'])}")
    print(f"  Gross margin:               {percent(results['gross_margin'])}")
    print(f"  Cost / connected minute:    {money(results['cost_per_connected_minute'])}")
    print(f"  Revenue / connected minute: {money(results['revenue_per_connected_minute'])}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI sales calling unit-economics calculator.")
    parser.add_argument("--provider", choices=PROVIDERS, default="twilio")
    parser.add_argument("--minutes", type=int, default=3000)
    parser.add_argument("--avg-call-minutes", type=float, default=3.0)
    parser.add_argument("--clients", type=int, default=2)
    parser.add_argument("--monthly-platform-fee", type=float, default=500.0)
    parser.add_argument("--setup-fee-per-client", type=float, default=750.0)
    parser.add_argument("--setup-fee-recognition-months", type=int, default=3)
    parser.add_argument("--usage-price-per-min", type=float, default=0.18)
    parser.add_argument("--booked-appointments", type=int, default=60)
    parser.add_argument("--success-fee", type=float, default=25.0)
    parser.add_argument("--fixed-monthly-cost", type=float, default=250.0)
    parser.add_argument("--no-amd", action="store_true")
    parser.add_argument("--record-calls", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario = Scenario(
        provider=PROVIDERS[args.provider],
        connected_minutes=args.minutes,
        average_call_minutes=args.avg_call_minutes,
        clients=args.clients,
        monthly_platform_fee=args.monthly_platform_fee,
        setup_fee_per_client=args.setup_fee_per_client,
        setup_fee_recognition_months=args.setup_fee_recognition_months,
        usage_price_per_min=args.usage_price_per_min,
        booked_appointments=args.booked_appointments,
        success_fee=args.success_fee,
        fixed_monthly_cost=args.fixed_monthly_cost,
        use_amd=not args.no_amd,
        record_calls=args.record_calls,
    )
    results = calculate(scenario, SarvamCosts())
    print_report(scenario, results)


if __name__ == "__main__":
    main()
