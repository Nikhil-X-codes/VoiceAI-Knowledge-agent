# Phase 4 Localization Evidence

## Configuration

| Market | Sector | ASR hint | TTS | Registers |
| --- | --- | --- | --- | --- |
| Philippines | Life insurance premium reminder | `tl`; `None` for Taglish; `en` for English | `fil-PH-BlessicaNeural`; English fallback `en-US-JennyNeural` | respectful, Taglish, English |
| Indonesia | Multifinance installment reminder | `id`; `jw` can be passed for Javanese tests | `id-ID-GadisNeural`; colloquial `id-ID-ArdiNeural` | formal, colloquial |

## Localization examples

### Philippines

| Generic English | Literal or blunt version | Localized version | Why |
| --- | --- | --- | --- |
| Your payment is overdue. | Direct overdue wording | `Pasensya na po, maaari po nating tingnan ang premium at mga payment option.` | Respectful `po` softens the reminder. |
| Pay via credit card. | Card-first wording | `Maaari po kayong gumamit ng GCash, bank, o Bayad centers.` | Uses familiar local payment channels. |
| I need a human. | `Wait for an agent.` | `Opo, ikokonekta ko po kayo sa isang kinatawan ngayon.` | Native handoff is clear and respectful. |

### Indonesia

| Generic English | Literal or blunt version | Localized version | Why |
| --- | --- | --- | --- |
| Your installment is due. | `Bayar sekarang.` | `Baik, Bapak/Ibu. Pembayaran cicilan dapat dilakukan melalui transfer, minimarket, atau e-wallet.` | Formal honorific and local channels avoid a blunt command. |
| I need help. | `Tunggu.` | `Baik, Kak. Saya bisa membantu mengecek pembayaran cicilan.` | Colloquial register is warmer and less abrupt. |
| I do not have that information. | `Saya tidak tahu.` | `Maaf, informasi itu belum tersedia. Saya dapat mengatur panggilan balik atau menghubungkan Bapak/Ibu dengan petugas.` | Gives a useful callback or handoff instead of ending the call. |

## ASR report

| Item | Philippines | Indonesia |
| --- | --- | --- |
| Provider / model | Groq `whisper-large-v3` | Groq `whisper-large-v3` |
| Languages configured | `en`, `tl`, Taglish auto-detect | `id`, `jw` test hint |
| Code-switching behavior | Taglish uses no forced language hint; recognizes English loanwords well | Indonesian finance terms remain in the Indonesian path |
| Empirical quality (10 utterances) | **Mean WER: 10.91%** (5/10 zero error) | **Mean WER: 11.57%** (7/10 zero error) |
| Observed errors | Spelled-out numbers vs digits (`five thousand` vs `5,000`), Taglish affixation (`na-lapse` recognized as `nalapsin`) | Spelled-out Rupiah amounts vs currency digits, DP acronym hyphenation (`DP-nya`) |
| Regional accent result | Not applicable | **0.0% WER** on Javanese (`id_09`) & Sundanese (`id_10`) clips with `id`/`jw` hints |

## Philippines vs Indonesia Comparison

| Dimension | Philippines (PH) Bot | Indonesia (ID) Bot |
| :--- | :--- | :--- |
| **Industry Sector** | Life Insurance / Bancassurance | Multifinance / Consumer Financing |
| **Conversation Objective** | Premium payment reminder & policy verification | Installment reminder & overdue debt counseling |
| **Honorifics / Politeness** | Respectful particles (`po`, `opo`) | Hierarchical honorifics (`Bapak/Ibu` for formal, `Kak` for warmer rapport) |
| **Tone on Delinquency** | Indirect, polite softening (`Pasensya na po...`) | Structured, solution-focused (`Baik, Bapak/Ibu...`) |
| **Local Payment Methods** | GCash, Bayad Centers, Philippine bank transfer | Minimarkets (Indomaret/Alfamart), VA bank transfer, e-wallets |
| **Currency & Numbers** | Philippine Peso (PHP), English/Tagalog mixed numbers | Indonesian Rupiah (`Rp`), spelled-out Indonesian numbering |
| **ASR Nuance** | Heavy Taglish code-switching (no forced ASR hint) | Regional accent phonetics (Javanese / Sundanese hints) |
| **Escalation / Handoff** | Human representative (`kinatawan`) | Human service officer (`petugas`) |

## Terminology Reference Lists

- **Philippines Life Insurance:** `premium`, `policy`, `beneficiary`, `rider`, `lapse`, `coverage`, `bank referral`, `GCash`, `Bayad`.
- **Indonesia Multifinance:** `cicilan`, `tenor`, `denda`, `DP (down payment)`, `jatuh tempo`, `angsuran`, `pembiayaan`, `minimarket`, `e-wallet`.

## Fallback and escalation checks

The localized tests verify that out-of-scope requests use native fallback lines and that human requests use native handoff lines. The shared server preserves the `market`, ASR hint, register, and TTS voice in every response.

- Philippines fallback: `Paumanhin po, wala po akong sapat na impormasyon. Maaari po akong mag-ayos ng tawag pabalik o maglipat sa isang kinatawan.`
- Philippines handoff: `Opo, ikokonekta ko po kayo sa isang kinatawan ngayon.`
- Indonesia fallback: `Maaf, informasi itu belum tersedia. Saya dapat mengatur panggilan balik atau menghubungkan Bapak/Ibu dengan petugas.`
- Indonesia handoff: `Baik, saya akan menghubungkan Bapak/Ibu dengan petugas kami sekarang.`

The configuration and tests are complete. Real native-speaker recordings and quality counts remain evidence work, not code blockers.

## Known gaps and compliance limits

- No native-speaker review has been completed yet; the generated call artifacts use scripted transcripts and Edge TTS fixtures.
- Philippine Insurance Commission requirements have not been legally reviewed.
- Indonesian OJK requirements have not been legally reviewed.
- Edge TTS voice quality, pronunciation of finance terms, and accent handling are compromises that require human review.
- The Javanese regional-accent case currently verifies the `jw` ASR hint and localized fallback path; a real Javanese or Sundanese recording is still required for degradation measurement.
