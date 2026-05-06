# Tijan AI — Project Memory

## Contexte
- **Fondateur:** Serigne Malick Tall (Malick), malicktall@gmail.com
- **Mission:** Premier fondateur non-technique a construire une licorne
- **Regle absolue:** Ne jamais suggerer d'embaucher ou de recruter un co-fondateur technique
- **Outils:** Claude Code (terminal), Claude mobile app, Cowork (desktop) — garder le contexte synchro partout

## What is Tijan?
Tijan AI is an **automated engineering bureau (bureau d'etudes automatise)** for West African construction projects. It generates structural calculations, MEP designs, BOQs, BIM plans, and EDGE certification reports — all Eurocode-compliant.

## Stack
- **Backend:** FastAPI 0.110.0 / Python 3.11 / Uvicorn (port 10000) on Render (build-ai-backend.onrender.com), repo ~/tijan-repo
- **Frontend:** React/Vite on Vercel (tijan.ai), repo ~/Downloads/tijan-frontend
- **Admin:** tijan-admin.vercel.app, repo ~/Downloads/tijan-admin
- **DB:** Supabase (projets, credits, payments, support tickets)
- **AI:** Anthropic Claude SDK + OpenAI (for parsing and chat)
- **PDF:** ReportLab + PyPDF + PyMuPDF
- **Office:** python-docx (Word), openpyxl (Excel)
- **CAD:** ezdxf (DXF), ODA + LibreDWG (DWG conversion), APS Design Automation (pro DWG output)
- **GitHub:** unicorn-builder/Tijan.ai-backend

## Architecture
- **32+ endpoints** covering: health, parsing, calculation, PDF/Excel/Word/DXF generation, chat, payments, translation
- **Lazy loading** — engine modules imported on first request
- **i18n** — French/English for all outputs
- **Multi-country** — Senegal, Cote d'Ivoire, Morocco, Nigeria, Ghana (auto-pricing by city)

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI app + all endpoints (~1843 lines) |
| `engine_structure_v2.py` | Structural calculations EC2/EC8 (~2000 lines) |
| `engine_mep_v2.py` | MEP calculations (~2000 lines) |
| `gen_*.py` | PDF/Excel/Word generators (FR + EN variants) |
| `generate_plans_*.py` | BA drawings, plumbing plans, architecture plans |
| `bim_model.py` | TijanBIM: Building/Level/Room/Wall/Equipment data model |
| `room_rules.py` | Room type equipment rules + trade definitions |
| `bim_parser.py` | Universal parser: any format → Building graph |
| `mep_router.py` | MEP topology-aware routing (plumbing/HVAC/elec/fire) |
| `bim_boq.py` | BIM-counted BOQ (equipment + network quantities from Building) |
| `bim_clash.py` | Clash detection engine (segment/equipment/structural conflicts) |
| `generate_plans_bim.py` | Unified plan dossier: cover + TOC + sublots + clash report (ReportLab) |
| `generate_plans_dxf.py` | Professional DXF/PDF renderer using ezdxf + CAD blocks |
| `mep_blocks.py` | 23 professional MEP block definitions for ezdxf (NF/EN symbols) |
| `parse_plans.py` | DWG/DXF/PDF parameter extraction (legacy) |
| `dwg_converter.py` | DWG to DXF conversion (ODA/LibreDWG/APS) |
| `aps_design_automation.py` | Professional DWG output via APS Design Automation |
| `prix_marche.py` | Market pricing database (5 countries) |
| `chat_engine.py` | LLM-based design assistant |
| `tijan_theme.py` | PDF branding/styling |

## Engineering Standards
- **Structural:** Eurocode 2 (EC2) for concrete, Eurocode 8 (EC8) for seismic
- **MEP:** French DTU standards, IT 246 (fire safety), IFC EDGE v3 (green certification)
- **Concrete classes:** C20/25 to C40/50 (auto-selected by project)
- **Steel:** HA400, HA500 (auto-selected)
- **Seismic zones:** Auto from country (Senegal zone 2, etc.)

## Regles de developpement
- Zero hardcoding — toutes les valeurs viennent des calculs reels
- Aucune fonction deboguee plus de 3 fois — reecrire si ca continue a echouer
- Monkey-patching de ReportLab Paragraph est INTERDIT
- JSX: pas de > au debut de ligne dans les balises <a>
- `from tijan_theme import *` n'exporte pas les variables prefixees `_`
- i18n: fichier i18n.jsx (pas .js), hook useLang/LangProvider, fonction t()
- Supabase RLS: utiliser auth.uid() = user_id + GRANT ALL explicite

## Anti-regression
- Toujours lancer `./scripts/pre_deploy_check.sh` avant git push
- 44 tests pytest doivent passer (tests/)
- Verifier `/version` endpoint apres deploy pour confirmer le bon commit

## Pipeline geometrie
- DXF → ezdxf direct (3966 murs Sakho valides)
- DWG → APS DXF output → ezdxf
- PDF vectoriel → pymupdf get_drawings() → coordonnees XY
- Layers Aasaman: A-WALL, A-DOOR, A-GLAZ, I-WALL

## Projet de reference
- Residence Papa Oumar Sakho, R+8, 32 unites, Dakar, Ref. 1711
- Beton C30/37 BPE 185,000 FCFA/m3, acier HA500B 520-540 FCFA/kg

## Testing
- `tests/test_endpoints.py` — endpoint tests (requires live backend)
- `tests/test_e2e.py` — end-to-end integration tests
- `tests/test_cors.py` — CORS verification
- `tests/test_dxf_pipeline.py` — DXF parsing
- `tests/test_pdf_geometry.py` — PDF geometry
- `scripts/pre_deploy_check.sh` — Pre-deployment gate (all test groups)
- **Base URL for tests:** https://build-ai-backend.onrender.com

## Deployment Flow
1. Push to `main` branch
2. Render auto-deploys (runs `build.sh` for ODA install + pip)
3. Starts `uvicorn main:app --host 0.0.0.0 --port 10000`

## CORS Origins
- tijan.ai, api.tijan.ai, admin.tijan.ai
- Vercel preview deployments
- localhost:5173/5174 (dev)

## Current Version
- **v6.1.0** (March 2026)

## Bug Fix History (April 2026)
### Stress test — 65+ bugs found and fixed:
- **engine_structure_v2.py:** Fixed column cross-section formula units, NRd capacity (removed wrong 0.8 factor), sqrt guard, VRd_c shear per EC2 6.2.2, pile capacity units, coffrage division-by-zero, seismic mass using actual loads, As_min per EC2 9.3.1.1, pile load using max()
- **engine_mep_v2.py:** Fixed EDGE ventilation ratio div/zero, documented peak flow coefficient, EDGE energy gain consistency, RIA length per IT 246, removed dead EDGE variables, fixed personnes_par_logement
- **main.py:** Fixed httpx import order, temp file resource leaks (6 endpoints), bare except clauses (9 locations), _parse_jobs thread safety, translate JSON parsing, input validation, guids empty check, httpx timeout, PayDunya env warnings
- **parse_plans.py:** Fixed PDF resource leaks, JSON parsing error handling
- **aps_parser_v2.py:** Thread-safe token cache, S3 finalization validation
- **chat_engine.py:** API key validation
- **extract_project_data.py:** None arithmetic protection
- **dwg_converter.py:** Path sanitization
- **gen_note_structure.py/en:** Proper exception logging
- **gen_mep.py/en:** EDGE attribute safety, cost ratio div/zero
- **gen_boq_xlsx.py:** C40/50 price lookup
- **generate_fiches_structure_v3.py:** Safe concrete class parsing

## Backlog — BIM Revolution (4 phases)
1. **Phase 1: TijanBIM Data Model** — DONE. `bim_model.py` (Building/Level/Room/Wall/Opening/Equipment graph), `room_rules.py` (equipment rules per room type, trade definitions), `bim_parser.py` (universal parser: PDF/DWG/DXF → Building graph). Fixes: no clim in WC/couloirs, prises on walls, all SDB have WC+lavabo+VMC.
2. **Phase 2: MEP Topology-Aware Routing** — DONE. `mep_router.py` — Plumbing router (colonnes montantes → distribution → fixtures, DTU 60.11 sizing), HVAC router (refrigerant to splits + VMC extraction + supply air), Electrical router (circuits per room, HCU + LCU), Fire safety router (SPK riser → main → branch + detection loop). All 4 routers tested: 342 segments routed across 36 rooms, zero orphan fixtures.
3. **Phase 3: Unified BIM Dossier** — DONE. `generate_plans_bim.py` (single PDF organized by trade × level with 14 sublots), `bim_boq.py` (equipment counted from BIM, not parametric formulas), `/generate-dossier-bim` endpoint (full pipeline: params → Building → equip → route → PDF + BOQ). BIM = single source of truth: plans and BOQ match exactly.
4. **Phase 4: Synthesis & Coordination** — DONE. `bim_clash.py` (clash detection: segment-vs-segment clearance, equipment-vs-network proximity, network-vs-structural-wall, electrical-above-plumbing per NF C 15-100). Multi-trade coordination plans with clash markers on SYN pages. Compiled deliverable: cover page, table of contents with page references, plan pages, clash report page. Next: IFC export + 3D viewer.

### Previous backlog (all DONE)
1. **Plans professionnels via Autodesk Design Automation API** — DONE.
2. **Modification d'étude depuis le chat** — DONE.
3. **Amélioration du design de la landing page** — DONE.

## Preferences
- Malick veut etre performant partout — keep code clean, fast, and safe
- Always run `scripts/pre_deploy_check.sh` before pushing
- Use French for user-facing content, English for code/comments
- Ne jamais suggerer d'embaucher — Malick construit tout avec Claude
