# Milestone Execution Plan — ConvMem–OpenClaw

**Current status (2026-09-27): SCHEMA-V3 PACKET TECHNICAL PASS;
PROVENANCE/LICENSING PAUSE; PRE-ACQUISITION AND CLEAN-REPLACEMENT PLAN-ONLY.** The accepted bounded implementation and
final M11 evidence remain preserved at
`PRESERVED_PR342_HEAD_SHA=94f29ebabee31112cccb223fd1445cb782aac6eb`.
Kiro passed the PR-corrective overlay `a23d843`; required GitHub `pytest (3.12)`
remains red with 83 failures, and the doctor/publisher corrections remain
unimplemented. Kiro passed the separate §18.23/§10.21 packet at `c63e52b`, after
which independent provenance/licensing reviews confirmed its exact disposition as
`PAUSE`. The first archive is immutable and rejected for publication. Kiro passed the
§18.24/§10.22 three-role replacement plan at `3402e62a`. Kiro passed schema v1
at `5f397852`; its offline P0 run proved the runtime tree and stopped on a component
initially classified as JSON null. Kiro passed schema v2 at `2956f701`; its one granted
run proved the raw `version` member is absent and correctly stopped before a result or
durable packet. Kiro passed schema v3 at `d03aa553`; Ryan then granted one collector
freeze and one offline P0 run. That run published the exact immutable packet at the
authorized read ceiling and honestly returned `PAUSE`/not build-eligible with 98,608
unresolved rows. Kiro passed §§18.28/10.26; Claude independently wrote disposition
`45442e93…`, and Codex verified technical `PASS`, provenance/licensing `PAUSE`, human
counsel required and all 98,608 IDs retained. Sections 18.29/10.27 now freeze lossless
pre-acquisition coverage and clean replacement for three host-path-bearing ELF objects.
Kiro passed that design at `a10a84d`; conflicting PR `#344` exposed a stale-base
STATUS conflict and an inherited fifth-file scope defect. This current-main
reconstruction preserves the four-document design but requires fresh exact-tip review.
They authorize no request, retained-source read, acquisition, binary repair, build,
runtime publication, evidence rerun, PR update or merge.

**Status:** M0–M8 BOUNDED GATE B/C ACCEPTED AT `8010fb0`; COMPLETE BOUNDED M11
EVIDENCE AND KIRO CONFORMANCE PASS PRESERVED AT `94f29eb`; PR `#342` MERGE
BLOCKED. RUNTIME BYTE/MODE/EXTRACTION VALIDATION PASS; PUBLIC REDISTRIBUTION
PROVENANCE/LICENSING FAIL/PAUSE. REPLACEMENT DELIVERY-SET PLAN KIRO PASS;
PRE-ACQUISITION AND CLEAN-REPLACEMENT PLAN AWAITS EXACT-TIP KIRO REVIEW.
PRODUCT/TEST/CI/RUNTIME EDITS, TEST EXECUTION, PR UPDATE, MERGE AND REAL OPENCLAW
WORK REMAIN PAUSED.

**Arc:** ConvMem Switchboard

## 0. Authority, scope, and interpretation

This is a sequencing and supervision overlay. Its semantic parent is exactly:

```text
SEMANTIC_PARENT_SHA=1b71fcc9958716323fa0b7a2467218f4e9fde5b0
PROVENANCE_MAIN_RECONCILIATION_BASE_SHA=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROVENANCE_ACQUISITION_PLAN_BASE_OVERLAY_SHA=3b3550c85f8c0482353dac55998d7b6f0fcbbbb0
P0_RESULT_BINDING_SEMANTIC_PARENT_SHA=9ecb10c3bb1b17b6190951037338f46d1f8e076b
PROVENANCE_SCHEMA_V3_RESULT_PLAN_BASE_OVERLAY_SHA=d03aa5538e0b82f1165a725394ef8df4bf805dbd
PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA=2956f70127544111d5d32e2f51a3e044fe878fb4
PROVENANCE_SCHEMA_V2_PLAN_BASE_OVERLAY_SHA=5f3978525c8685f59329ccae78d184d4a1822b4b
PROVENANCE_SCHEMA_V1_PLAN_BASE_OVERLAY_SHA=3402e62a8479011814bfa76ce9e1c3269dc34350
RUNTIME_REPLACEMENT_PLAN_BASE_OVERLAY_SHA=c63e52be138d0c101e8898dee929e33c33267672
RUNTIME_DELIVERY_PLAN_BASE_OVERLAY_SHA=a23d84390daa6b784d61b86b112361023363aae8
PR342_PLAN_BASE_OVERLAY_SHA=dc060312469551d4b9b18f1233588e6780689cad
PR342_BASE_SHA=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PRESERVED_PR342_HEAD_SHA=94f29ebabee31112cccb223fd1445cb782aac6eb
PRESERVED_PR342_TREE_SHA=391fc01d64d36b783fe6da768da7ff37a423470f
PR342_FAILED_PYTEST_JOB=108602309599
PR342_REQUIRED_CONTEXT=pytest (3.12)
R2B_PRECORRECTION_COMMITTED_IDENTITY=b716152fbf725633a55371f6acf7ed5580a704bd
R2B_PRECORRECTION_RESOLVED_IDENTITY=e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b
R2B_FINAL_MEMBER_COUNT=120
PROPOSED_CI_RUNTIME_TAG=switchboard-fixture-runtime-74a12c725ac3bad4f
PROPOSED_CI_RUNTIME_ASSET=switchboard-fixture-runtime.tar.gz
PROPOSED_CI_RUNTIME_TREE_SHA256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
QUALIFIED_RUNTIME_ARCHIVE_SIZE=557628743
QUALIFIED_RUNTIME_ARCHIVE_SHA256=6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e
QUALIFIED_RUNTIME_COMPLETE_EXTRACTED_TREE_SHA256=52d3f70a9eb64b5c5348abc8c487994acba7fe7de0b77c358175ff42cfd23d37
QUALIFIED_RUNTIME_PACKET_SHA256=24073ab433c503c1d5721984b97fe957ccada0ce634f8bdeae4e8ed1f9907a7d
QUALIFIED_RUNTIME_PUBLICATION_ELIGIBLE=false
QUALIFIED_RUNTIME_LICENSING_DISPOSITION=PAUSE
REJECTED_RUNTIME_ARCHIVE_SHA256=6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e
REJECTED_RUNTIME_PUBLICATION_ELIGIBLE=false
REPLACEMENT_DELIVERY_SET_STATUS=PLAN_ONLY
REPLACEMENT_PROVENANCE_CLOSURE=UNRESOLVED
REPLACEMENT_LICENSING_DISPOSITION=PAUSE
REPLACEMENT_PUBLICATION_ELIGIBLE=false
PROVENANCE_SCHEMA_VERSION=convmem.switchboard.provenance-lock.v3
PROVENANCE_INPUT_RUNTIME_ROOT=/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROVENANCE_INPUT_RUNTIME_TREE_SHA256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
PROVENANCE_INPUT_RUNTIME_REGULAR_FILE_COUNT=30421
PROVENANCE_PACKET_FILE_ROLE_COUNT=13
PROVENANCE_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3
PROVENANCE_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3
PROVENANCE_DURABLE_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
PROVENANCE_DURABLE_REVIEW_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review
PROVENANCE_PACKET_STATUS=PAUSE
PROVENANCE_EXECUTION_AUTHORIZED=false
PROVENANCE_V3_COLLECTOR_FREEZE_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-collector-freeze/1cb8186e5e0938524414c530d5b842219f52412f/d03aa5538e0b82f1165a725394ef8df4bf805dbd
PROVENANCE_V3_COLLECTOR_SHA256=26352b39f3ff53bf8a41c579c4c9aec8a8f8734235fe99db0a8480fa9964adad
PROVENANCE_V3_COLLECTOR_SIZE=67575
PROVENANCE_V3_COLLECTOR_FREEZE_SHA256=c8f457b589b6554a33921965339a74db086806d9243bb5fa4565df39b5e74ada
PROVENANCE_V3_COLLECTOR_DIFF_SHA256=be6b82f89aaac51cc8ae1cbaace78d111dc0f00de92ee7a45009d57d182f59a5
PROVENANCE_V3_RESULT_PATH=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/p0-result.json
PROVENANCE_V3_RESULT_SHA256=db755121a38ffa43587662337bf896196a944bdaaf0019e899c13bc0afb43045
PROVENANCE_V3_RESULT_SIZE=20155
PROVENANCE_V3_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
PROVENANCE_V3_MANIFEST_SIZE=2957
PROVENANCE_V3_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
PROVENANCE_V3_PACKET_BYTES=654147403
PROVENANCE_V3_OBJECT_COUNT=651
PROVENANCE_V3_OBJECT_BYTES=600094627
PROVENANCE_V3_COMPONENT_COUNT=1221
PROVENANCE_V3_NESTED_COMPONENT_EDGE_COUNT=1384
PROVENANCE_V3_OWNED_FILE_COUNT=30402
PROVENANCE_V3_UNOWNED_OR_AMBIGUOUS_FILE_COUNT=19
PROVENANCE_V3_UNRESOLVED_COUNT=98608
PROVENANCE_V3_RUNTIME_CONTENT_PASS_COUNT=5
PROVENANCE_V3_RUNTIME_READ_BYTES=11643965233
PROVENANCE_V3_NEGATIVE_CONTROL_COUNT=65
PROVENANCE_V3_BUILD_ELIGIBLE=false
PROVENANCE_V3_REVIEW_ROOT_PRESENT=true
PROVENANCE_V3_REVIEW_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
PROVENANCE_V3_REVIEW_DISPOSITION_SIZE=8383806
PROVENANCE_V3_REVIEWED_AT_UTC=2026-09-27T21:34:24Z
PROVENANCE_V3_TECHNICAL_VERDICT=PASS
PROVENANCE_V3_PROVENANCE_VERDICT=PAUSE
PROVENANCE_V3_LICENSING_VERDICT=PAUSE
PROVENANCE_V3_HUMAN_COUNSEL_REQUIRED=true
PROVENANCE_V3_OPEN_UNRESOLVED_COUNT=98608
PROVENANCE_V3_PUBLICATION_ELIGIBLE=false
PROVENANCE_COMPONENT_PRIMARY_KEY_SHA256=b6b73ee112f898acf91c37ac0ad4e704ddd0fe131d3bcc5599c62d81bcf12146
PROVENANCE_FILE_PRIMARY_KEY_SHA256=432a960cd59db58b5c0345ff5179f71fb3aa7bb7a8780b3b5d2a072f390fb7aa
PROVENANCE_NESTED_EDGE_PRIMARY_KEY_SHA256=2c144bbd5a6d5e0a477a841847c5d9700de60c8a9488c546d09b13c138a3b580
PROVENANCE_UNRESOLVED_PRIMARY_KEY_SHA256=2f207467c9e9308eda47a0dd762e361d687c7f6d614a46a810b8a43fc4554838
PROVENANCE_COMPONENT_BATCH_COUNT=20
PROVENANCE_COMPONENT_BATCH_SIZE=64
PROVENANCE_FINAL_COMPONENT_BATCH_SIZE=5
PROVENANCE_UNRESOLVED_PAGE_COUNT=49
PROVENANCE_UNRESOLVED_PAGE_SIZE=2048
PROVENANCE_FINAL_UNRESOLVED_PAGE_SIZE=304
PROVENANCE_OWNERSHIP_DISPUTE_FILE_COUNT=19
PROVENANCE_ACQUISITION_STATUS=PLAN_ONLY
HOST_PATH_REMEDIATION_STATUS=PLAN_ONLY
PROVENANCE_ACQUISITION_EXECUTION_AUTHORIZED=false
HOST_PATH_TCL_RUNTIME_PATH=lib/libtcl8.6.so
HOST_PATH_TCL_OBJECT_ID=obj_sha256:a69a8d60eb3240f152a22f42f99e3bbd15ba60dc9d232615709406511d057d9b
HOST_PATH_TCL_OCCURRENCE_COUNT=8
HOST_PATH_TK_RUNTIME_PATH=lib/libtk8.6.so
HOST_PATH_TK_OBJECT_ID=obj_sha256:3aef1cd676469b0e6d0402d3db3d74b9a64d25b3988adf069f8eae112a3dde0c
HOST_PATH_TK_OCCURRENCE_COUNT=1
HOST_PATH_TINFO_RUNTIME_PATH=lib/libtinfow.so.6
HOST_PATH_TINFO_OBJECT_ID=obj_sha256:60ecdf843974955b99a8b0e63d2167915ca046c88e01a7c0245a1fa3a380c8d8
HOST_PATH_TINFO_OCCURRENCE_COUNT=1
PROVENANCE_V1_FIRST_COLLECTOR_SHA256=e84cf1e633541b9a7343bbaf78457573cf041e7f59f0cc71d6c7be8d491de59e
PROVENANCE_V1_FIRST_INCORRECT_PROJECTION_SHA256=22da33da243b6fa7a7e75abe1e290fae22f2bf1d7ae87bb78ea4fd981b2e4bc4
PROVENANCE_V1_RETRY_COLLECTOR_SHA256=c9ef70f2a728cac680a1227b5bafc5533a3211f244e1abbf2f89906749eae028
PROVENANCE_V1_RUNTIME_CONTENT_PASS_COUNT=2
PROVENANCE_V1_RUNTIME_READ_BYTES=4537493452
PROVENANCE_V1_EVIDENCE_FILE_COUNT=780
PROVENANCE_V1_EVIDENCE_BYTES=600463206
PROVENANCE_V1_CYCLONEDX_DOCUMENT_COUNT=13
PROVENANCE_V1_CYCLONEDX_COMPONENT_COUNT=1371
PROVENANCE_V1_UNREPRESENTABLE_COMPONENT_COUNT=1
PROVENANCE_V1_SBOM_OBJECT_SHA256=d3c068f4be653f38b8f6fca1dd1a9d1b41dc712dc9c3daa01b0e0f84882324d6
PROVENANCE_V2_COLLECTOR_SHA256=737aa48f1b6d99111e98ac0bd5b75445b1896ed937d5676e404b8630ad0c220f
PROVENANCE_V2_COLLECTOR_DIFF_SHA256=3065e94c18525191ebed2759001ec399b042131f8ad1214cccdc6a102dfb7c78
PROVENANCE_V2_COLLECTOR_RECEIPT_SHA256=c5d63d15468eb2270ebf9c1002aa7640b784159d33499c2737623f24a5047a1b
PROVENANCE_V2_EXIT_STATUS=1
PROVENANCE_V2_RUNTIME_CONTENT_PASS_COUNT=1
PROVENANCE_V2_RUNTIME_READ_BYTES=2568978329
PROVENANCE_CUMULATIVE_RUNTIME_CONTENT_PASS_COUNT=3
PROVENANCE_CUMULATIVE_RUNTIME_READ_BYTES=7106471781
PROVENANCE_V2_EVIDENCE_FILE_COUNT=780
PROVENANCE_V2_EVIDENCE_BYTES=600463206
PROVENANCE_V2_PARTIAL_OBJECT_COUNT=651
PROVENANCE_V2_PARTIAL_OBJECT_BYTES=600094627
PROVENANCE_V2_SBOM_COMPONENT_CANONICAL_SHA256=820f3546548cdbcda11395dbeeb274485b71582c0316bf0518d78fe7d209994b
PROVENANCE_V2_SBOM_COMPONENT_KEY_SET_SHA256=1516b75285ffd5cd81f18728ba54daa50a5991ea5e63c0b00a4d71bb26bda2ee
PROVENANCE_V2_SBOM_VERSION_KEY_PRESENT=false
QUALIFIED_RUNTIME_BWRAP_PACKAGE=bubblewrap_0.9.0-1ubuntu0.3_amd64.deb
QUALIFIED_RUNTIME_BWRAP_SHA256=2461f1beee9cb04c8942739fe1a2b37e7b7c2a3d518f0779dc75f9245baa3094
ORIGINAL_CODE_BASELINE_SHA=7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
ACCEPTED_IMPLEMENTATION_SHA=8010fb060c2edc29e1b09d7a30b1a1da2689d489
INTEGRATION_BASELINE_SHA=9193f5ec744f059d07a20612489b210527b5660a
PRIOR_CURRENT_MAIN_BASELINE_SHA=a92a74eb326b3eaa59087b707de10153c7cc0c63
CURRENT_MAIN_BASELINE_SHA=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PRESERVED_M11_EVIDENCE_BRANCH=feat/2026-09-23-openclaw-convmem-m11-integration
PRESERVED_THREE_TIP_PREFLIGHT_BRANCH=feat/2026-09-26-openclaw-convmem-m11-main-reconciliation
PRESERVED_ADVANCED_MAIN_BRANCH=feat/2026-09-26-openclaw-convmem-m11-main-advance
PRESERVED_INTEGRATION_TIP=a11b7a2a793c68e4e6e83c2680b077389a817c5c
RECONCILIATION_BASE_OVERLAY_SHA=581de2abf430786a36f2612f97c623a19b61353f
PYLINT_PLAN_BASE_OVERLAY_SHA=c5513d50b656f9cc9e6423ea819438f975d16ee5
PYTEST_PLAN_BASE_OVERLAY_SHA=67d4f5aa62415f3550fbc56a760374cf3c19ee23
PYTEST_IDENTITY_PLAN_BASE_OVERLAY_SHA=b0358464caf493992810137e40c8ed619e7af932
M8_AUTHORITY_PLAN_BASE_OVERLAY_SHA=b1b2341a4f98701f5784631f866c5405174c7414
BUNDLE_SCHEMA_PLAN_BASE_OVERLAY_SHA=57285608b2ee9ec5950201968bc533b8830a6ea8
AUTHORITY_PACKET_PLAN_BASE_OVERLAY_SHA=6b1b90b4865dc0b92e0ead470136eeebc3bd8447
CURRENT_MAIN_PLAN_BASE_OVERLAY_SHA=fc5289a18db4a8ea0a8f215e2148b2b6aba3b41d
THREE_TIP_PLAN_BASE_OVERLAY_SHA=b5d0c96dc0837ae515db0787ac136c308b25aaad
CURRENT_MAIN_ADVANCE_PLAN_BASE_OVERLAY_SHA=05e0d79712fdb7c9d2e5640b8c4a744d3f84e56b
INNER_ROLE_SIGNATURE_PLAN_BASE_OVERLAY_SHA=5b14010302021dcd7dc579f5714517a0f26570e1
PYLINT_RECONSTRUCTION_PLAN_BASE_OVERLAY_SHA=95011db461d51dcd3960a375757418401c5e505b
PYLINT_ACCEPTANCE_DRIFT_PLAN_BASE_OVERLAY_SHA=35e1fc34691ad6f0a662d9a0175a9f1ae1f4d9a8
PYLINT_R0401_DETERMINISM_PLAN_BASE_OVERLAY_SHA=6106f61e5a8661302ed4b83ac48215c08352a255
M8_LEGACY_COUNT_PLAN_BASE_OVERLAY_SHA=60731421eaf76aa6e69ff39ab5030b8d8a4f0a24
PRESERVED_M11_TIP=9c6421a6891fd8a861a51f4fed410f541b53148c
PYTEST_DIFFERENTIAL_BASE_SHA=9c6421a6891fd8a861a51f4fed410f541b53148c
PRESERVED_M11_CANDIDATE_SHA=3f8ef8312e3f3c98915320bd1b988bac5d8d96a9
PRESERVED_M11_DIFFERENTIAL_PAUSE_SHA=853ef98ede44f2d171e5354b065e11f83558e010
PRESERVED_M11_M8_PAUSE_SHA=7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af
PRESERVED_M11_BUNDLE_SCHEMA_PAUSE_SHA=d7b15926ab7e4e41b8a80edba5edbe4bfed4c165
PRESERVED_M11_AUTHORITY_PACKET_PAUSE_SHA=851edbe49b820bd4081809022b10f67c30fef47a
PRESERVED_M11_MERGE_READY_SHA=cd60cf19dca6706e4175e9f82c9ba55e41bca10b
PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA=30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca
PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA=d276cb4ab0a0613b965e772d49d378e761df337e
PRESERVED_M11_INNER_ROLE_PAUSE_SHA=776a4ca3d4215490fb26b882dca2df9a41e0e03a
PRESERVED_M11_PYLINT_PAUSE_SHA=65bbfd6f47515accfefa110b667afe1613f0dbed
PRESERVED_M11_PYLINT_ACCEPTANCE_PAUSE_SHA=c71d37a42de0937aff57a2af47770a89902f132a
PRESERVED_M11_R0401_PAUSE_SHA=caec5c6868f600e897b29a39f555365e5f818ac1
PRESERVED_M11_M8_COUNT_PAUSE_SHA=9da6dd98d276b250470de4e53ac786f7547d92d5
PRIOR_CURRENT_MAIN_DELTA_PATH_COUNT=40
PRIOR_CURRENT_MAIN_DELTA_PATH_SET_SHA256=596a484cbf550a63bf77ac559733455aceadef75aaa5d3d8a6fee417b6695e6b
CURRENT_MAIN_ADVANCE_PATH_COUNT=11
CURRENT_MAIN_ADVANCE_PATH_SET_SHA256=0566d14e2246970abe77a89736db01a95ae89cb88d2c9556f33c14b6bf7c484c
CURRENT_MAIN_DELTA_PATH_COUNT=45
CURRENT_MAIN_DELTA_PATH_SET_SHA256=670241f7690afc18cf8689c7406ac6d86d395bfc323acfc5f2f72a85a46c853e
PRESERVED_THREE_TIP_DELTA_PATH_COUNT=124
PRESERVED_THREE_TIP_DELTA_PATH_SET_SHA256=af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314
REVIEWED_DELTA_PATH_COUNT=124
REVIEWED_DELTA_PATH_SET_SHA256=af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314
PRODUCT_DELTA_PATH_COUNT=120
PRODUCT_DELTA_PATH_SET_SHA256=60903bc194bd6e471f6c7009df30ab0832cad7a5505e9fd14b2c64450d27c659
CURRENT_MAIN_R2B_IDENTITY=b716152fbf725633a55371f6acf7ed5580a704bd
RECONSTRUCTED_R2B_IDENTITY=e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b
R2B_MEMBER_COUNT=120
R2B_PATH_SET_SHA256=fb062070b962265bfce6c2cc2b709eca4b2d5f7a8d1a516d5b3599bcb0361ec8
PYTEST_DIFFERENTIAL_PAUSE_LEDGER_SHA256=3c2a50d1a61578fa235524bc26493a2b1458ba60d729b039c0a66d27ddce0c1e
PYTEST_DIFFERENTIAL_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/3317913e74997f97a135339b596461b1f8080626/9193f5ec744f059d07a20612489b210527b5660a/runs/853ef98ede44f2d171e5354b065e11f83558e010/m11-full-pytest-differential-pause
M8_PAUSE_CLASSIFICATION_SHA256=e217e5607640b5f1985ad57256f7911fc8b409364ecc25c5f98e22c25082105c
M8_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/9c5c2bf7d3c5b6d9f13d68329b6f7112c25cabe1/9193f5ec744f059d07a20612489b210527b5660a/runs/7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af/m11-m8-run1-final
BUNDLE_SCHEMA_PAUSE_CLASSIFICATION_SHA256=c25ece6380d0b1cf4989a010419307dfdc29c2ecc31b9c4dd47faaee23b89148
BUNDLE_SCHEMA_DRIFT_SHA256=50a82638e4265c910dcdf7422d193bb6178ff29c51e175dd05fa1949cc4713d5
BUNDLE_SCHEMA_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/48c9ce01bf557ff95fd82b84c3b0ab2e7e9f18cb/9193f5ec744f059d07a20612489b210527b5660a/runs/d7b15926ab7e4e41b8a80edba5edbe4bfed4c165/m11-m8-run1-final
AUTHORITY_PACKET_PAUSE_CLASSIFICATION_SHA256=3fbfab4bac23c30325961d21a974ec4ed03229759c1b974686d323c061982c77
AUTHORITY_PACKET_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/b46a16a3cdc928e98fba83cd64b17439d1734695/9193f5ec744f059d07a20612489b210527b5660a/runs/851edbe49b820bd4081809022b10f67c30fef47a/m11-m8-run1-final
CURRENT_MAIN_DIFFERENTIAL_COMPARISON_SHA256=03873a4d4e368e5b5fd3de86140e3fd9b74525c3e83b966275d556fd9728693b
CURRENT_MAIN_DIFFERENTIAL_PAUSE_LEDGER_SHA256=3bd89ebf3dd016d5fc709215862ae491688cb878c3477fbd9f21f3619b2d256e
CURRENT_MAIN_DIFFERENTIAL_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/33767acaf563c25e8fbd9984f08316f1ba4b1b27/a92a74eb326b3eaa59087b707de10153c7cc0c63/runs/30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca/m11-current-main-pytest-differential
SWITCHBOARD_CANDIDATE_ONLY_NODE_COUNT=238
SWITCHBOARD_CANDIDATE_ONLY_IDENTITY_SHA256=fe50be2f51456d85efdf80305af83a7d0fa224110cd4980a27da74ed46e291b8
SWITCHBOARD_CANDIDATE_ONLY_IDENTITY_OUTCOME_SHA256=2c03a11c8c5d66b822b406e35deb6874be0dd4301fe78d51780da96977b4c607
SWITCHBOARD_CANDIDATE_ONLY_PASSED_COUNT=160
SWITCHBOARD_CANDIDATE_ONLY_PASSED_IDENTITY_SHA256=b98f02f3f6d8b1c14b9d0e90e4dbb0f8e67e12698842ab37b381f5f4b2c35ae1
SWITCHBOARD_CANDIDATE_ONLY_FAILED_COUNT=78
SWITCHBOARD_CANDIDATE_ONLY_FAILED_IDENTITY_SHA256=e3fdc26e69739af0ff33282378d02d6d930416daa8b89fc6964825ecd6e08423
INNER_ROLE_SIGNATURE_NODE_COUNT=22
INNER_ROLE_SIGNATURE_NODE_SET_SHA256=9fa64e04c15b96cbb935cb5b40d4e47a9cdd5869099d728a5213174c7244cbf6
INNER_ROLE_PAUSE_LEDGER_SHA256=a6a2d95b6f294ad3893ea39fa8c739b15a7ea172d2067757492c49abf49399a6
INNER_ROLE_DIAGNOSTIC_SHA256=115492f91adeaf71aa09afd81b66e863191d0e7306efdd2a51a1168633c0376d
INNER_ROLE_PAUSE_MANIFEST_SHA256=78ac1cef55142892cdf75d2cad71a22a536519a4d27359fedba04881020e1c80
INNER_ROLE_RERUN_PLAN_SHA256=15d082c9805943a11c4c6236c5f23e48bf64440aa8b60cda29b25c2ad55eddcd
INNER_ROLE_PRELIMINARY_COMPARISON_SHA256=674f79845a763293128e5e2d95230c0ded1c296a42fa0365061e9f4a089f1f91
INNER_ROLE_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/538d37eb498e2d3bd497db33daa006520ad56d06/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/776a4ca3d4215490fb26b882dca2df9a41e0e03a/m11-three-tip-pytest-differential/comparison
PYLINT_PRIOR_PAUSE_LEDGER_SHA256=28c3db4d0450c37d2a36079c1d960318161dcf8dc3c1cabf1f0082a21357f45b
PYLINT_TRIAGE_LEDGER_SHA256=53eb6004562c89854189961f5b8303de09d43d436ebd7070ed5676a581f48757
PYLINT_TRIAGE_MANIFEST_SHA256=c9734c355b4d6d997ce4d163d6ba76893f13dd71049c132564c9353f57c6f3d3
PYLINT_INTRODUCED_PAIR_COUNT=3
PYLINT_INTRODUCED_PAIR_FILE_SHA256=ab41f0096d024331fd06ce9d49eed0f0800e73f65668766bd806a2e2e3a70671
PYLINT_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/9faac8ea87532bc73f74b788b38234de0c614a4e/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/65bbfd6f47515accfefa110b667afe1613f0dbed
PYLINT_ACCEPTANCE_PAUSE_LEDGER_SHA256=fe268988c98e944b679446f3551987eaeccf9dce9a2b3b0963896069148a3e62
PYLINT_ACCEPTANCE_PAUSE_MANIFEST_SHA256=6f631cb97c8ae3531f70dc38a4fd5c865b3965ae207bac7b06ccd072cb15c01f
PYLINT_ACCEPTANCE_REPORT_SHA256=e114236db43b888184a3847631a1025031e31385c55664e2304d024618cd7a2b
PYLINT_ACCEPTANCE_PAIR_COMPARISON_SHA256=a61465a3f448dcf98a6a583cc5d8f334e7831783443b2e6568044b72fa616301
PYLINT_ACCEPTANCE_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/3656104081a790676b02f1057bbc552631ce96d0/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/c71d37a42de0937aff57a2af47770a89902f132a/m11-pylint-final
PYLINT_R0401_PAUSE_LEDGER_SHA256=b7fddc9534540a28116e62646e2989f80e6cd5f3d3efecc30a06649195f10860
PYLINT_R0401_PAUSE_MANIFEST_SHA256=9076aacd8185b88e73e1381fc1cb5706c1fd50b64609b8ce31a668438eb0d85d
PYLINT_R0401_REPORT_SHA256=044f723a77946bd3b6c593dcea10987d7956ab62a5a58789dc2b23215553eeaf
PYLINT_R0401_EQUIVALENCE_SHA256=cafe5c059255fc82d6c2b538c3505a2168312aef87788ff420002dd2537e104c
PYLINT_R0401_DRIFT_SHA256=a606e77bf639f13350107ceee6ac7131b5f867b4310b9d195f88c1b8a9d9abd1
PYLINT_R0401_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/c92bc708d1fc23e8d37584890e876c151682a48d/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/caec5c6868f600e897b29a39f555365e5f818ac1/m11-pylint-final
PYLINT_R0401_PROBE_SUMMARY_SHA256=c68834661b2362a1e43a762460ab36a00077b91570fcb95767179d296ebef34b
PYLINT_R0401_PROBE_AUTHORITY_SHA256=cbeb6e3d6253f17907ff25e109576a680d028333908f167ccf39e1589b71c8fe
PYLINT_R0401_PROBE_MANIFEST_SHA256=2cff8fe59f2e703e0183d175b33000b0b9d89e2651baf5dd0bf67bcff0d22eed
PYLINT_R0401_PROBE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/c92bc708d1fc23e8d37584890e876c151682a48d/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/caec5c6868f600e897b29a39f555365e5f818ac1/m11-pylint-r0401-determinism-probe
PYLINT_R0401_RECORDS_SHA256=e0a2c3d9e41e204deff7fdc68265d2a4ed2952934b4eaea42a79fe22dfa09282
PYLINT_R0801_PAIRS_SHA256=51d818973d3f9054ff35e1ba721adadb281fa0eac61a929fda7b02c5fee78556
PYLINT_MESSAGE_ID_COUNTS_SHA256=278ff3c7e0935c2b2426635a5c178f15ff0a0e3fb7943c16281fda111391c896
M8_LEGACY_COUNT_PAUSE_LEDGER_SHA256=73005d7a3b65d5de6652696c92a6801789b0051a90b399755c8e4c3854ce8aa8
M8_LEGACY_COUNT_PAUSE_MANIFEST_SHA256=51bf7fef728223106a1da8f7dfeb3de42bce8a7e15d2e3830c0919eeabe7152d
M8_LEGACY_COUNT_DIAGNOSTIC_SHA256=a025ada8c43533577ed8a204f16317865b0e2beb7edd80687aa28a1184f48264
M8_LEGACY_COUNT_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/45863c87f1ae70b89dd063da8f09f6cd16fdb3a3/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/9da6dd98d276b250470de4e53ac786f7547d92d5/m11-m8-run1-final
PRESERVED_THREE_TIP_UNUSED_SLOT=/home/lauer/.cache/convmem-m11-three-tip-differential/300180f7c0a382b6e7d85b2858a338c271ce695e/slot
PRESERVED_THREE_TIP_UNUSED_EVIDENCE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/300180f7c0a382b6e7d85b2858a338c271ce695e/a92a74eb326b3eaa59087b707de10153c7cc0c63/runs/d276cb4ab0a0613b965e772d49d378e761df337e/m11-three-tip-pytest-differential
PROPOSED_FIXED_EXECUTION_SLOT=/home/lauer/.cache/convmem-m11-m8-legacy-count/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/slot
PROPOSED_RUNTIME_PREFIX=/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROPOSED_DURABLE_EVIDENCE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
ARCHITECTURE=docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
EXECUTION=docs/plans/EXECUTION-openclaw-convmem-integration.md
```

After Ryan confirms that root, exact plan-review artifacts go only under
`PROPOSED_DURABLE_EVIDENCE_ROOT/planning-reviews/`; M11 run evidence goes only
under `PROPOSED_DURABLE_EVIDENCE_ROOT/runs/<integration-source-commit>/<run-label>/`.
Codex verifies every volatile-to-durable byte/hash mapping. These paths are
evidence stores, not authority, approval, production data or a ConvMem corpus.

The two parent documents define every schema, field, hash, state transition,
interface, error, limit, identity, test case, and allowed path. This overlay
does not replace, loosen, or reinterpret them. A conflict stops work and goes
to Codex/Kiro; Grok must not choose between readings. M0–M8 proved only the
parent's synthetic T0–T5 Gate B/C fixture on the original baseline. M11 must
preserve and re-prove that exact implementation on the integration baseline
before merge readiness. Gate D real
runtime, Gate W governed writes, Gate D-V value evaluation, Gate E pilot/live
use, Gate F expansion, watch configuration, and promotion remain separately
blocked.

The runner's single `--plan-sha` is always `SEMANTIC_PARENT_SHA`. The overlay
SHA is the exact final branch tip Kiro reviews and Ryan later names as
`REVIEWED_OVERLAY_SHA`; it is not substituted into the parent's runner
contract. The final overlay descends from `SEMANTIC_PARENT_SHA`; this current-main
reconciliation starts at `PROVENANCE_MAIN_RECONCILIATION_BASE_SHA`. The original
reviewed provenance-acquisition/clean-replacement branch started at
`PROVENANCE_ACQUISITION_PLAN_BASE_OVERLAY_SHA`. The preceding schema-v3 result-binding
branch started at `PROVENANCE_SCHEMA_V3_RESULT_PLAN_BASE_OVERLAY_SHA`; its semantic
parent is retained as `P0_RESULT_BINDING_SEMANTIC_PARENT_SHA`. The preceding schema-v3
design branch started at `PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA`.
The preceding schema-v2 branch started at
`PROVENANCE_SCHEMA_V2_PLAN_BASE_OVERLAY_SHA`. The preceding schema-v1 branch started at
`PROVENANCE_SCHEMA_V1_PLAN_BASE_OVERLAY_SHA`.
The preceding replacement-plan branch started at
`RUNTIME_REPLACEMENT_PLAN_BASE_OVERLAY_SHA`.
The preceding runtime-delivery branch started at
`RUNTIME_DELIVERY_PLAN_BASE_OVERLAY_SHA`.
The preceding PR-corrective branch started at `PR342_PLAN_BASE_OVERLAY_SHA`.
Every earlier evidence branch and
correction tip remains immutable historical provenance. The current preserved
implementation input is `PRESERVED_PR342_HEAD_SHA`; it is not rebased, merged,
force-pushed or rewritten by this plan. After Kiro PASS and new Ryan grants,
Cursor applies only the grant-named reviewed plan/scope range and the held doctor,
publisher/recovery and CI corrections, pushing and stopping after each. An
independent lane then rotates only the R2b inventory. Codex alone executes the
fresh evidence defined in M11. The
historical `AUTHORITY_PACKET_PLAN_BASE_OVERLAY_SHA`, `PYLINT_PLAN_BASE_OVERLAY_SHA` and
`PYTEST_PLAN_BASE_OVERLAY_SHA` and `PYTEST_IDENTITY_PLAN_BASE_OVERLAY_SHA`
and `M8_AUTHORITY_PLAN_BASE_OVERLAY_SHA` and `BUNDLE_SCHEMA_PLAN_BASE_OVERLAY_SHA`
remain evidence of already-applied ranges and are never replayed. The current
main-reconciliation range begins after `PROVENANCE_MAIN_RECONCILIATION_BASE_SHA`
and is not an evidence, acquisition or implementation range. The original
pre-acquisition, result-binding, schema-v3, replacement-plan and
runtime-delivery ranges remain reviewed history and are never replayed. The earlier §18.22 corrective may be applied to a
grant-named branch preserving `PRESERVED_PR342_HEAD_SHA` only after its separately
required runtime and Ryan gates pass.

Ryan's R-PROFILE-REFUSAL ruling ratifies the baseline selector normalization
`(value or "").strip().lower()`. When the semantic parent does not explicitly
freeze refusal presentation, exact stderr bytes and numeric exit codes are
noncontractual implementation details. Tests bind the specified semantic
failure class and effects, never implementation-derived presentation: nonzero
exit, empty stdout, no registration/start/effect, no raw-value disclosure, and
any parent-required semantic instruction. This rule applies consistently to
profile, fixture, CLI, publisher, and runner refusals; an explicitly frozen
parent error contract still controls.

Ryan's 2026-09-23 M8 node-inventory ruling authorized only that completed
correction: the two frozen Python commands may emit pytest's built-in JUnit XML under
disposable `/fixture/evidence`, solely for exact collected node IDs and
outcomes. The parent freezes the output paths, xunit1 mapping, canonical
evidence shape and fail-closed parser. Selectors, four deselections, selected
test logic, dependencies, permissions, containment and runtime behavior remain
unchanged. The accepted M8 PASS does not transfer to the M11 integration tree.

The Grok-facing actualization brief at commit
`e476e0e01db9a3d25ed3f1037e49293324434dfc`,
`docs/inter-model/GROK-2026-09-21-openclaw-convmem-actualization-brief.md`, is
implementation detail only. The semantic parent governs behavior; this
overlay governs milestone order, holds, and supervision. Any conflict
stops work. Its Steps 0–9 govern detailed task decomposition where consistent;
the actualization brief never overrides either governing document. This
overlay expressly supersedes that brief's `READY FOR ... EXECUTE DECISION`
status, single-`REVIEWED_PLAN_SHA` authority packet, Step 0.1 grant wording,
and Step 0.2 instruction for Grok to create the branch. The brief is not an
authorization source; the overlay's two-SHA grant and Codex-created worktree
procedure control.

Review and authority order is mandatory:

1. Opus's adversarial `BUILD FAIL` on overlay `9243765` is reconciled here.
2. Ryan's written R-PROFILE-REFUSAL ruling ratifies baseline normalization and
   makes parent-unspecified refusal presentation noncontractual; it authorizes
   this overlay-only correction and no implementation.
3. Kiro PASSed overlay `d1ca459` with semantic parent `cd9d2698`; Ryan then
   granted bounded M0–M8 implementation.
4. The node-evidence correction was implemented; two accepted fresh-root runs
   and exact-tip Kiro conformance review established bounded M8 TEST PASS at
   `8010fb060c2edc29e1b09d7a30b1a1da2689d489` under parent `3433813` and
   overlay `b16763f`.
5. Ryan accepted bounded M0–M8 and authorized M11 merge-readiness. Codex's
   baseline audit found that current main `9193f5e` and the accepted
   implementation require explicit reconstruction and new evidence; Codex
   issued `PAUSE` rather than silently rebasing.
6. Kiro reviewed the current-main reconciliation overlay `581de2a`; Ryan
   authorized M11. The exact 45-commit replay and pin/comment reconciliation
   were completed, held, inspected and preserved at `a11b7a2`.
7. The first fresh M8 attempt stopped before source export, imports or tests:
   the outer runner reported the four reviewed plan/STATUS paths as product
   allowlist violations. Codex retained the evidence and issued `PAUSE`.
8. Ryan authorized the reviewed-plan correction from `581de2a`; Kiro passed its
   final overlay `c5513d5`. Ryan then granted exact application, bounded
   correction and M8 retry. The resulting clean pushed tip is `9c6421a`.
9. At `9c6421a`, two fresh M8 runs and the seven legacy MCP regressions passed.
   The unchanged current-main Pylint gate failed on 699 new occurrences. Codex
   retained the evidence and issued `PAUSE` rather than raising a baseline or
   weakening CI.
10. Ryan directed Codex to choose the durable lint resolution. Kiro passed the
    reviewed plan; Ryan granted the exact 44-path remediation. The corrected
    candidate is clean and pushed at `PRESERVED_M11_CANDIDATE_SHA`; its unchanged
    current-main Pylint gate passes with no new/increased fingerprint.
11. The first complete repository pytest attempt retained failures. Independent
    diagnostics reproduced structural failures at both `PRESERVED_M11_TIP` and
    the candidate, proving an unconditional full-pytest PASS claim inapplicable.
    Codex issued `PAUSE`; Ryan authorized this plan-only differential correction.
12. Kiro passed differential overlay `b035846` with semantic parent `3317913`.
    Ryan granted only its plan application and Codex-owned evidence sequence.
    Grok applied the exact reviewed plan range and pushed
    `PRESERVED_M11_DIFFERENTIAL_PAUSE_SHA`; Codex verified the four document
    blobs and non-plan-byte identity before continuing.
13. Complete baseline/candidate runs collected equal 2,912-node sets and equal
    outcome totals but produced 28 signature mismatches: 23 path/repr effects
    and five R2b authority-content identity rotations. Codex emitted
    `PYTEST_DIFFERENTIAL_PASS=false`, retained the exact PAUSE ledger, and ran
    no later evidence after the stop.
14. Ryan authorized the plan-only identity reconciliation; Kiro passed parent
    `9c5c2bf` and overlay `b1b2341`. Ryan granted its exact application and
    evidence sequence. Grok applied the reviewed range; the clean pushed source
    is `PRESERVED_M11_M8_PAUSE_SHA`.
15. Codex established `PYTEST_DIFFERENTIAL_PASS=true` with 2,912 equal nodes,
    233 identical debt nodes and the exact five R2b rotations, then re-proved
    the unchanged current-main Pylint gate. The first final M8 run refused
    before fixture creation because embedded parent/overlay literals remained
    bound to the preceding reviewed packet. Codex retained the PAUSE and ran no
    M8 run 2 or MCP regression.
16. Ryan authorized the plan-only M8 authority-packet reconciliation; Kiro
    passed parent `48c9ce0` and overlay `57285608`. Ryan granted its exact plan
    application, two-file/four-literal rebind and evidence sequence. Grok
    applied the plans and correction; the clean pushed candidate is
    `PRESERVED_M11_BUNDLE_SCHEMA_PAUSE_SHA`. Codex re-established the complete
    differential and unchanged Pylint gate, then M8 run 1 reached the strict
    suite and produced 28 failures at one invented production bundle-schema
    literal. Codex retained the PAUSE and ran no M8 run 2 or MCP regression.
17. Ryan authorized the plan-only bundle-schema reconciliation; Kiro passed
    parent `b46a16a3` and overlay `6b1b90b4`. Ryan granted their exact
    application, the one-file/one-literal publisher correction and evidence
    sequence. Grok applied the plans and correction; the clean pushed candidate
    is `PRESERVED_M11_AUTHORITY_PACKET_PAUSE_SHA`. Codex re-established the
    complete differential and unchanged Pylint gate. Final M8 run 1 then
    refused before source export or fixture creation because the fixture packet
    remained bound to preceding parent `48c9ce01…` and overlay `57285608…`.
    Codex preserved classification `AUTHORITY_PACKET_PAUSE_CLASSIFICATION_SHA256`
    and ran no M8 run 2 or MCP regression.
18. Ryan authorized the plan-only post-bundle authority-packet reconciliation;
    Kiro passed parent `67de0d7` and overlay `fc5289a`. Ryan granted their exact
    application, the two-file/four-literal correction and final evidence. The
    resulting clean pushed candidate is `PRESERVED_M11_MERGE_READY_SHA`.
    Codex established the governed differential, unchanged current-main Pylint
    gate, two fresh M8 PASSes, seven MCP regression PASSes and durable-evidence
    verification; Kiro exact-tip conformance review passed.
19. Ryan delegated the merge-readiness decision to Codex. A fresh fetch found
    `origin/main` at `CURRENT_MAIN_BASELINE_SHA`, twelve commits beyond the
    historical integration baseline. The reviewed candidate and current main
    both change the governed STATUS document, and `git merge-tree` reports a
    real content conflict. No PR existed. Codex issued `PAUSE` rather than
    rebasing, resolving the conflict, transferring old evidence, or merging.
20. Ryan authorized this plan-only current-main reconciliation. Kiro must
    review this exact new parent/overlay. Ryan may then grant only creation of
    the new branch from `CURRENT_MAIN_BASELINE_SHA`, the three held commits and
    the fresh current-main evidence defined in M11. Silence, an earlier grant
    or any old `CONTINUE` is not authorization.
21. Kiro passed that plan and Ryan granted the exact reconstruction. Grok made
    the held 120-path product, four-blob control-plane and six-literal identity
    commits; Codex independently verified exact composition. The clean pushed
    result is `PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA`.
22. Complete pytest at current main and the reconstructed candidate finished
    under identical conditions. All 2,686 current-main nodes were retained;
    238 additional Switchboard nodes were observed, 160 passed and 78 failed.
    Every one of those 238 nodes already exists in
    `PRESERVED_M11_MERGE_READY_SHA` with the same outcome. Because §18.14
    nevertheless required every candidate-only node to pass or skip, Codex
    sealed `CURRENT_MAIN_DIFFERENTIAL_PASS=false`, preserved the comparison and
    PAUSE ledger hashes, and ran no Pylint/M8/MCP evidence. Ryan authorized only
    that plan correction.
23. Kiro passed semantic parent `300180f7` and overlay `05e0d797`; Ryan granted
    the exact plan/rebind/evidence sequence. The held plan and four-literal
    commits were independently verified and preserved at
    `PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`; the runtime rebind also passed.
    Before a suite or evidence slot existed, the mandatory check found
    `origin/main=5c6a4a8` rather than the grant-frozen `a92a74e`. Codex issued
    `PAUSE`; no pytest, Pylint, M8 or MCP process ran.
24. Kiro passed the advanced-current-main plan and Ryan granted it. The new
    branch was reconstructed in three held commits, independently verified,
    pushed and preserved at `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. Three complete
    pytest runs and all 166 isolated reruns completed; the finalizer then issued
    `PAUSE` on unstable pytest `os.environ` rendering for exactly 22 unchanged
    inner-role assertion failures. Pylint, M8 and MCP did not run.
25. Ryan authorized only the plan-only inner-role signature correction. Kiro
    passed semantic parent `9faac8ea` and overlay `95011db4`; Ryan granted the
    exact plan/rebind/evidence sequence. Grok applied the reviewed plans and
    four-literal rebind. Codex then established the fresh three-tip differential
    at `PRESERVED_M11_PYLINT_PAUSE_SHA`, with the closed 238-node, five-node
    R2b and 22-node semantic-signature proofs all passing.
26. The unchanged full-tree Pylint command then produced 458 findings and 72
    `R0801` messages; the protected gate exited 1 because the aggregate
    duplicate-code fingerprint increased from baseline 71 to 72. Codex sealed
    `PYLINT_PRIOR_PAUSE_LEDGER_SHA256`; M8 and MCP did not run.
27. Ryan authorized one read-only current-main triage. In the identical
    revalidated CI environment, `CURRENT_MAIN_BASELINE_SHA` produced 455
    findings and 69 `R0801` messages and passed the unchanged gate. The sealed
    `PYLINT_TRIAGE_LEDGER_SHA256` proves exactly three candidate-introduced
    pairs; no source/runtime correction occurred.
28. Ryan authorized that plan-only post-reconstruction Pylint correction; Kiro
    passed it and Ryan granted the exact held sequence. Grok applied the plan,
    four-literal rebind and two-test-file correction in separate verified
    commits. Final source is preserved at
    `PRESERVED_M11_PYLINT_ACCEPTANCE_PAUSE_SHA`.
29. Codex reran the complete `N1`/`R`/final-candidate comparison and all 166
    reruns. The 238-node, five-node R2b and 22-node inner-role proofs passed and
    established `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` for that exact tip;
    retained debt keeps `FULL_PYTEST_PASS=false`.
30. The unchanged Pylint command completed with 456 findings, 71 `R0801` and
    240 fingerprints. The protected gate exited zero, but the stronger exact
    §18.18 acceptance failed because two pairs were added relative to `N1`.
    Codex sealed `PYLINT_ACCEPTANCE_PAUSE_LEDGER_SHA256`; M8/MCP did not start.
31. Ryan authorized only this plan-only acceptance-drift correction. Kiro
    passed it and Ryan granted the held plan/rebind/source/evidence sequence.
    Grok applied the reviewed plans, four-literal rebind and exact one-file
    correction in separate verified commits. Final source is preserved at
    `PRESERVED_M11_R0401_PAUSE_SHA`.
32. Codex reran the complete `N1`/`R`/final-candidate comparison and all 166
    reruns. The 238-node, five-node R2b and 22-node inner-role proofs passed and
    established `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`; retained debt keeps
    `FULL_PYTEST_PASS=false`.
33. The unchanged Pylint command completed with 458 findings, 29 `R0401`, 69
    `R0801` and 240 fingerprints. The protected gate exited zero and the exact
    pair multiset equaled `N1`, but §18.19's 454-total rule failed. Codex sealed
    `PYLINT_R0401_PAUSE_LEDGER_SHA256`; M8/MCP did not start.
34. Ryan authorized exactly four non-acceptance determinism probes and this
    plan-only correction. With the sole environment addition
    `PYTHONHASHSEED=0`, two `N1` and two final-source runs all reproduced
    458/29/69/240 and identical canonical semantic identities. Raw report bytes
    differed and are explicitly non-authoritative. Kiro passed the correction,
    Ryan granted the held sequence, and the reviewed plans plus four-literal
    rebind were applied and preserved at `PRESERVED_M11_M8_COUNT_PAUSE_SHA`.
35. Codex reran the complete `N1`/`R`/final-candidate comparison and all 166
    reruns. The 238-node, five-node R2b and 22-node inner-role proofs passed and
    established `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`; retained debt keeps
    `FULL_PYTEST_PASS=false`. Paired seeded Pylint then passed exact §18.20
    semantic acceptance at both tips.
36. Final M8 run 1 completed 238 strict passes, 29 Node passes and legacy
    118 collected / 117 passed / one skipped / four deselected. The outer
    parser correctly issued `PAUSE` because the historical expected count was
    still 116/115. Independent comparison proved exactly two added passing
    current-main safety nodes, no removal and no outcome change. Codex sealed
    `M8_LEGACY_COUNT_PAUSE_LEDGER_SHA256`; run 2 and MCP did not start.
37. Ryan authorized only this plan-only legacy-count correction. Kiro exact-tip
    review and a new Ryan resume grant remain mandatory before plan application,
    four-literal rebind, the one-path/two-integer correction or any suite.
38. That sequence subsequently completed. Exact tip `PRESERVED_PR342_HEAD_SHA`
    passed the fresh differential, unchanged Pylint, two M8 runs, seven MCP
    regressions, durable verification and Kiro conformance. Ryan separately
    authorized PR creation; PR `#342` was opened against `PR342_BASE_SHA`.
39. The required GitHub `pytest (3.12)` context failed with 83 failures while
    CodeQL, secret scan and Pylint passed. Focused ultrareview independently
    confirmed the doctor-import containment and fenced-retry/recovery defects.
40. Ryan authorized Astra to design and Codex to encode only the bounded
    cross-arc plan correction. Astra returned DESIGN READY / MERGE BLOCKED.
    Kiro then passed exact overlay `a23d843`. That PASS authorizes no implementation,
    runtime publication, evidence retry, PR update or merge.
41. Ryan authorized only the qualified-runtime delivery packet and one disposable
    local deterministic archive from the frozen source. Codex verified every source
    content hash/mode before and after the read, built and safely extracted the exact
    archive, and froze its hashes/counts and pinned bubblewrap recipe in §18.23/§10.21.
42. The local byte/mode/extraction verdict is PASS. Historical provisioning does not
    bind complete redistributable component provenance/licensing, so the packet
    freezes `PUBLICATION_ELIGIBLE=false`, `LICENSING_DISPOSITION=PAUSE`. Kiro later
    passed the packet at `RUNTIME_REPLACEMENT_PLAN_BASE_OVERLAY_SHA`; no external
    release or implementation was authorized.
43. Codex's independent provenance/licensing review returned publication FAIL/PAUSE,
    and Kiro independently concurred against the frozen bytes. The first archive is
    immutable rejected diagnostic evidence. The reviews confirmed incomplete sysroot
    license/source material, unbound Node/build provenance, incomplete nested-component
    inventory and missing installed Apache license copies.
44. Ryan authorized Codex to author only the replacement delivery-set correction.
    Architecture §18.24 and Execution §10.22 define a new runtime archive, compliance/
    corresponding-source archive and canonical manifest behind separately reviewed and
    granted lock, build, final-packet, publication and CI-admission stages.
45. Kiro returned exact-tip PASS on the replacement plan at
    `PROVENANCE_SCHEMA_V1_PLAN_BASE_OVERLAY_SHA`. That PASS approved design/scope only
    and did not authorize provenance execution, a build or publication.
46. Ryan then authorized only the provenance-lock schema-v1 packet. Architecture §18.25
    and Execution §10.23 freeze thirteen file roles, canonical encodings, separate
    immutable packet/review roots, cross-file closure, source authority and negative
    controls. Kiro passed the exact v1 overlay at `5f397852`.
47. Ryan authorized an offline P0 execution and one bounded collector retry. The retry
    corrected only inventory-row `sha256:<64-hex>` encoding, proved the exact runtime
    tree, and stopped on the sole JSON-null version among 1,371 CycloneDX components.
    No durable packet/review root exists; v1 staging is rejected PAUSE evidence.
48. Ryan authorized only this schema-v2 plan. Architecture §18.26 and Execution §10.24
    define one closed immutable-GitHub-revision projection under fresh roots. No retry,
    runtime/evidence read, packet creation, network request or build is authorized.
49. Kiro passed schema v2 at `PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA`. Ryan then
    granted one offline P0. The frozen collector completed one runtime inventory and
    the bounded evidence copy, then correctly refused because the raw `base64`
    component omits `version`. No result, ledger, manifest, durable packet or review
    root exists; v2 staging is rejected PAUSE evidence.
50. Ryan authorized only this schema-v3 plan. Architecture §18.27 and Execution §10.25
    freeze the one exact raw-object-bound absent-member projection under fresh roots.
    No collector freeze, retry, runtime/evidence read, packet creation, network request
    or build is authorized.
51. Kiro passed schema v3 at `PROVENANCE_SCHEMA_V3_RESULT_PLAN_BASE_OVERLAY_SHA`.
    Ryan then separately authorized the frozen collector and one offline P0 execution.
    Codex completed it once at the exact cumulative read ceiling, published immutable
    packet tree `PROVENANCE_V3_PACKET_TREE_SHA256`, and independently verified every
    object and staging-to-durable byte/mode mapping. At that checkpoint the packet was
    `PAUSE`, not build-eligible, with 98,608 open rows and no review root. Architecture
    §18.28 and Execution §10.26 bind only that result and the next independent-review
    hold.
52. Kiro passed the result-binding overlay at
    `PROVENANCE_ACQUISITION_PLAN_BASE_OVERLAY_SHA`. Ryan separately authorized Claude
    as independent reviewer; Claude atomically wrote the sole disposition, and Codex
    independently verified `PROVENANCE_V3_REVIEW_DISPOSITION_SHA256`, all twelve
    packet-file hashes, all 98,608 open IDs and the unchanged packet tree. Technical
    verdict is `PASS`; provenance/licensing remain `PAUSE`; human counsel is required.
53. Ryan authorized only this pre-acquisition and host-path remediation design. Astra
    ruled that one contract may cover both while granting neither. Architecture §18.29
    and Execution §10.27 freeze lossless component/file/edge/unresolved coverage,
    candidate-versus-authority separation, exact later-operation requirements and
    clean replacement for three packet-owned path-bearing ELF objects. No request,
    retained-source read, acquisition, repair, build or implementation is authorized.

## 1. State ledger

| State | Items |
|---|---|
| **Specified** | Semantic parent Architecture §§18.22–18.29 and Execution §§10.20–10.27; the accepted T0–T5 contract; exact doctor containment; fenced publication/recovery semantics; complete ordinary/qualified pytest partition; rejected first runtime archive; three-role replacement delivery set; canonical provenance-lock schema; exact-object absent-member projection; immutable v3 P0 result and disposition; lossless pre-acquisition coverage; clean replacement for host-path-bearing ELFs; static 120-member R2b convergence; held file sets; supervision; and final evidence. |
| **Implemented** | Historical bounded M0–M8 and M11 implementation/evidence are preserved. PR `#342` is open at `PRESERVED_PR342_HEAD_SHA`. No §18.22/§10.20 corrective product, test, CI, inventory or runtime-distribution change has been implemented. |
| **Tested** | Historical isolated M8, MCP, Pylint and Kiro conformance evidence passed at the exact preserved source. On PR `#342`, CodeQL, secret scan and Pylint pass; required GitHub `pytest (3.12)` fails with 83 nodes across the frozen 22/56/5 families. Focused ultrareview confirmed the doctor and publisher defects. The first runtime archive passed exact source/content/mode, header, closed extraction and post-read mutation checks, while independent provenance/licensing reviews returned publication FAIL/PAUSE. Kiro passed the replacement-plan design at `3402e62a`, schema v1 at `5f397852`, schema v2 at `2956f701`, schema v3 at `d03aa553` and result binding at `3b3550c`. The v1/v2 P0 stops remain rejected. The single v3 P0 completed with five cumulative passes and 11,643,965,233 bytes, one exact projection, 65 negative controls and zero network/external/retained-source reads; its durable packet verifies but retains 98,608 unresolved rows. Claude's disposition and Codex verification confirm technical PASS/provenance-and-licensing PAUSE and the three captured host-path findings without reading the runtime. |
| **Assumed** | Nothing unavailable is accepted as working. Hosted-runner compatibility remains a fail-closed future preflight. Local byte qualification does not imply public redistribution clearance. |
| **Unresolved** | Kiro exact-tip review of this pre-acquisition/clean-replacement parent and overlay; complete cited origin work items; separately reviewed and Ryan-granted metadata/acquisition operations; zero-unresolved lock closure; clean replacement build and qualification; final packet and licensing review; Ryan's later external-publication and implementation grants; held doctor, publisher/recovery, CI and R2b inventory corrections; fresh evidence; focused safety review; Kiro integrated-tip PASS; and Ryan merge decision. Real OpenClaw and Gates D/W/D-V/E/F remain independently blocked. |

## 2. Dependency order

```text
M0 baseline/runtime input
  → M1 T0a isolated runner and production refusal
  → M2 T0b schemas, vectors, inventories, and independent oracles
  → M3 T1–T2 scope/state/authority/publication
  → M4 T3 read-only CLI/MCP
  → mandatory Gate B review hold
  → M5 T4 uninstalled connector
  → mandatory T4 hold
  → M6 T5 fake controller/manager/supervisor
  → M7 bounded evidence package
  → M8 final isolated adversarial runs and bounded TEST PASS [accepted]
  → M11a current-main plan reconciliation, review and Ryan grant [complete]
  → M11b exact replay and pin/comment reconciliation [preserved at a11b7a2]
  → M11c pre-test allowlist PAUSE [observed; no test ran]
  → M11d reviewed-plan correction, M8/MCP PASS, Pylint PAUSE [9c6421a]
  → M11e revision-safe Pylint plan correction and exact-tip Kiro PASS
  → M11f 44-path remediation and unchanged Pylint PASS [3f8ef83]
  → M11g applicability plan applied; first differential PAUSE [853ef98]
  → M11h path/identity reconciliation applied; differential/Pylint PASS [7f2a2e2]
  → M11i final M8 packet PAUSE before fixture/runtime use [7f2a2e2]
  → M11j two-file/four-literal packet reconciliation applied [d7b1592]
  → M11k differential/Pylint PASS; final M8 run 1 schema-literal PAUSE [d7b1592]
  → M11l one-file/one-literal publisher correction applied [851edbe4]
  → M11m differential/Pylint PASS; final M8 run 1 packet PAUSE [851edbe4]
  → M11n post-bundle packet correction and all final evidence PASS [cd60cf19]
  → M11o current-main drift audit and merge PAUSE [a92a74e]
  → M11p exact-current-main reconstruction [30bc134d]
  → M11q complete current-main differential applicability PAUSE [30bc134d]
  → M11r three-tip correction and held plan/rebind [d276cb4]
  → M11s three-tip evidence preflight PAUSE on main advance [5c6a4a8]
  → M11t advanced-current-main reconstruction [776a4ca3]
  → M11u complete three-tip runs/reruns; inner-role signature PAUSE [776a4ca3]
  → M11v closed signature correction, fresh differential PASS and Pylint PAUSE [65bbfd6f]
  → M11w read-only Pylint triage; three candidate-introduced pairs proved
  → M11x first Pylint correction; fresh differential PASS; exact Pylint PAUSE [c71d37a]
  → M11y acceptance-drift plan/rebind/source correction applied [caec5c6]
  → M11z fresh differential PASS; exact Pylint R0401-rule PAUSE [caec5c6]
  → M11aa deterministic-Pylint plan/rebind applied; fresh differential and
    paired Pylint PASS [9da6dd98]
  → M11ab final M8 run 1 legacy-count PAUSE [9da6dd98]
  → M11ac plan-only 118/117 successor-count correction
  → Kiro exact-tip review and Ryan exact M8-count resume grant
  → reviewed plan range onto 9da6dd98; held four-literal rebind;
    held one-path/two-integer count correction
  → fresh N1/R/final-candidate differential with closed 22-node proof
  → paired N1/final Pylint with PYTHONHASHSEED=0, exact 458/29/69/240,
    three canonical semantic hashes and both raw reports retained
  → two fresh M8 runs at exact 118/117 legacy count; seven MCP files;
    integration review
  → Kiro integrated-tip PASS and Ryan PR creation decision
  → PR #342 created at exact head 94f29eb; required pytest (3.12) FAIL
  → focused ultrareview: doctor containment and fenced-retry blockers confirmed
  → plan-only §18.22/§10.20 safety, CI and R2b convergence corrective
  → Kiro exact-tip plan PASS at a23d843
  → plan-only §18.23/§10.21 qualified-runtime delivery packet and local validation
  → Kiro exact-tip packet PASS at c63e52b
  → independent provenance/licensing FAIL/PAUSE; first archive rejected
  → plan-only §18.24/§10.22 replacement delivery-set correction
  → Kiro exact-tip replacement-plan PASS at 3402e62a
  → plan-only §18.25/§10.23 provenance-lock schema packet
  → Kiro exact-tip schema-v1 PASS at 5f397852
  → offline P0 runtime-tree PASS; one-component SBOM-version PAUSE; no durable packet
  → plan-only §18.26/§10.24 schema-v2 projection under fresh roots
  → Kiro exact-tip schema-v2 PASS at 2956f701
  → one schema-v2 P0; exact absent-member PAUSE; no result/durable packet
  → plan-only §18.27/§10.25 schema-v3 exact-object projection under fresh roots
  → Kiro exact-tip schema-v3 PASS at d03aa553
  → separate Ryan collector-freeze and single offline P0 grants
  → immutable schema-v3 packet PAUSE at exact read ceiling; 98,608 open rows
  → plan-only §18.28/§10.26 exact result/manifest/packet binding
  → Kiro exact-tip result-binding PASS at 3b3550c
  → separate Ryan independent-reviewer grant; exact disposition 45442e93…
  → technical PASS; provenance/licensing PAUSE; human counsel required
  → plan-only §18.29/§10.27 lossless pre-acquisition and clean-replacement contract
  → Kiro exact-tip pre-acquisition design review
  → complete cited component/ownership work-item planning; unknown origins unresolved
  → separate exact metadata/acquisition operation packet, review and Ryan grant
  → bounded Codex acquisition at fresh coordinates
  → zero-unresolved lock closure plus Kiro and independent provenance/licensing review
  → separate reviewed clean-build recipe and Ryan build grant; deterministic
    three-role replacement build across two disposable prefixes
  → independent qualification and plan-only final packet
  → Kiro final-packet review plus independent actual-byte licensing review
  → separate Ryan external-publication and CI-admission decisions
  → separate Ryan implementation decision
  → held five-document plan application and authority/scope rebind
  → held doctor containment correction
  → held publisher/recovery correction
  → held ordinary/qualified CI adapter correction
  → independent held R2b inventory rotation
  → fresh CI/Pylint/M8/MCP/safety evidence and Kiro integrated-tip review
  → Ryan merge decision only with required GitHub checks green

M8 → M9 Gate W ─┐
M8 → M9 Gate D ─┼→ M10 Gate D-V, then Gate E → M11 complete review
                └─ W and D remain independent, separately reviewed/granted
```

M0–M8 and the preceding M11 evidence are accepted historical scope; they are neither
reopened nor promoted into a green GitHub required check. M9, M10, watch coverage and
complete-system review remain decision gates, not implementation work. The only
possible next activity is exact-tip Kiro review of this pre-acquisition and clean-
replacement plan.
Because the replacement freezes `REPLACEMENT_PROVENANCE_CLOSURE=UNRESOLVED`,
`REPLACEMENT_LICENSING_DISPOSITION=PAUSE` and
`REPLACEMENT_PUBLICATION_ELIGIBLE=false`, Kiro PASS cannot
authorize origin resolution, provenance acquisition, binary repair, build or publication.
Each requires its own reviewed packet and Ryan grant. A separate later Ryan grant may let Cursor perform only
M11's held file sets in order, pushing and stopping at every checkpoint. Codex
independently proves every diff and owns all fresh evidence. Ryan alone decides merge.
No earlier grant, evidence result, branch, plan range or `CONTINUE` can be reused.

## 3. Milestones

### M0 — Current-state audit and frozen baseline

1. **Name and purpose:** Establish exact, reproducible starting bytes.
2. **Architectural outcome:** The accepted implementation was based on
   `ORIGINAL_CODE_BASELINE_SHA`
   and governed by `SEMANTIC_PARENT_SHA`; no silent rebase, ambient state, or
   branch helper that silently substitutes `origin/main`.
3. **Affected surfaces:** Git worktree/branch, supplied runtime prefix, and
   read-only inventories only; no product file changes.
4. **Preconditions/dependencies:** Kiro PASS on this exact overlay/parent;
   Ryan's exact T0–T5 grant; a branch Codex created at
   `ORIGINAL_CODE_BASELINE_SHA`; clean
   dedicated worktree; and the exact parent-frozen runtime supplied by Ryan or
   the one provisioning operator explicitly named in Ryan's grant; and one
   durable evidence location designated by Ryan for reviews and M7/M8 output.
5. **Implementation tasks:** Codex creates and pushes the implementation branch
   from `ORIGINAL_CODE_BASELINE_SHA` without using
   `convmem work start`, because that helper branches from current
   `origin/main`. Codex copies the cited parent-review reports to the designated
   durable location and verifies their recorded hashes. From the shared
   checkout, Grok runs exactly
   `convmem work resume <branch> --worktree` to enter that pre-created branch;
   it must not use the default resume mode or switch the live checkout. Record
   base/tip/upstream; install repo-local Git settings;
   inventory tracked files, dependency versions, Ryan-supplied runtime bytes,
   protected bytes, and the parent-defined allowlist. Grok does not provision,
   download, install, or repair runtime dependencies.
6. **Tests/evidence:** `git status --short`, exact base/merge-base/tree checks,
   explicit upstream/refspec, source/runtime manifests, exact CPython/Unicode/
   Node/MCP/idna versions, protected-byte/mode comparison, and dependency
   inventory.
7. **Invariants:** No live data/config access; no OpenClaw process; no edit on
   `main`; never check out the implementation branch in
   `/home/lauer/Projects/convmem`; semantic parent remains exact.
8. **Forbidden changes:** Fetch-derived baseline substitution, rebase, schema,
   config, credential, persistent-state, permission, dependency, or host
   runtime mutation.
9. **Done:** Clean implementation branch at the exact baseline with recorded
   inventories, supplied exact runtime, designated durable evidence location,
   and zero implementation diff.
10. **Ryan confirmation:** Yes for the exact T0–T5 grant and for runtime
    provisioning. No routine reapproval after those exact grants unless a
    stop condition or governing SHA change occurs.
11. **Live inspection:** Codex checks branch/base/worktree, status, diff,
    tracked and runtime inventories, dependencies, grant text, provisioner
    identity, and protected-byte report; then cites the pushed M0 commit in a
    written `CONTINUE`.
12. **Verdict:** Separate ConvMem verdict; OpenClaw is not run.

### M1 — T0a isolated runner and fail-closed production refusal

1. **Name and purpose:** Build physical containment first and prove every
   bypass fails before importing integration code.
2. **Architectural outcome:** The only acceptance entrypoint is the parent's
   closed `run_isolated.py`; production fake/controller/supervisor/plugin
   selection refuses before OS action.
3. **Affected surfaces:** Test-only fixture-manifest schema,
   `tests/fixtures/openclaw_strict/run_isolated.py`, production-refusal seams
   in the parent-listed controller/supervisor/connector paths, and the exact
   strict/connector test paths named by Execution §5.1.
4. **Preconditions/dependencies:** M0 `CONTINUE`; exact runtime prefix and
   grants present; no integration module has been imported or executed.
5. **Implementation tasks:** Implement the exact four-argument runner,
   runtime/component preflight, fixed mounts/namespaces/environment/FD closure,
   source allowlist, pre-import sentinel, capacity bounds, and all T0a negative
   mutants. Create every fixed strict and connector test path at T0a as a
   collection-safe, test-first assertion file: no placeholder success, skip,
   or xfail is allowed. Later-T tests must be red only because their frozen
   capability is absent, never because a file is missing or collection fails.
6. **Tests/evidence:** Run only the exact runner CLI with
   `--plan-sha SEMANTIC_PARENT_SHA`. At this checkpoint the
   overall suite is expected red; case 57's pre-import/containment portion and
   every runner bypass mutant must be green before the declared future-T reds.
   Evidence includes import/process/network/FD/mount traces proving no strict
   integration import occurred before preflight.
7. **Invariants:** No integration code is imported or run outside
   `run_isolated.py`; no host fallback; no missing runtime byte is installed;
   no overall TEST claim is made.
8. **Forbidden changes:** Subset mode, arbitrary command/mount/suite,
   permissive fallback, host `/usr`, host test execution called acceptance,
   stub implementation, real gateway/model/provider, or production fake.
9. **Done:** All T0a controls pass inside the unchanged closed runner; every
   remaining red is mapped to a later T step; the pushed commit has Codex
   `CONTINUE`. Bounded TEST remains NOT YET RUN/PASS.
10. **Ryan confirmation:** No within the exact grants; yes for runtime/host
    provisioning, another runner interface, or any production selection.
11. **Live inspection:** Codex checks the pushed commit, full diff/file list,
    every command Grok ran outside the runner, raw runner output, import
    sentinel, mounts, dependencies, permissions, and the declared red map.
12. **Verdict:** ConvMem containment/refusal verdict only; no OpenClaw verdict.

### M2 — T0b ConvMem preservation and closed integration contract

1. **Name and purpose:** Encode the frozen schemas, bytes, inventories, and
   independent oracles without changing legacy ConvMem semantics.
2. **Architectural outcome:** Closed schemas/vectors, mandatory IDNA runtime,
   five component inventories, legacy-byte preservation, and independently
   recomputed hashes exist before T1 code.
3. **Affected surfaces:** Exact Gate B/C schemas in parent Execution §2;
   mandatory `requirements.txt` line `idna==3.18` if absent;
   `tests/fixtures/openclaw_strict/**`; and the fixed test-first files.
4. **Preconditions/dependencies:** M1 `CONTINUE`; exact parent schema and
   component sets copied without inference.
5. **Implementation tasks:** Implement schema validators, protocol fixtures,
   known-answer hashes/IDs, two independent canonical parsers, five reference-
   owned component walkers, legacy envelope preservation, and disposable-copy
   mutation controls. The `idna==3.18` pin is required, never optional, and is
   included in every parent-defined component digest that contains it.
6. **Tests/evidence:** T0b oracle tests and case 58's artifact/membership
   portions that are executable before T1; duplicate/unknown/reordered/
   wrong-type/missing-null rejection; exact legacy bytes; included/excluded
   mutation behavior; omitted-`canonical_json.py` mutant. Overall runner may
   remain red only for declared T1–T5 tests; no whole-case-58 PASS is claimed.
7. **Invariants:** Legacy IDs, envelope UUIDs, provenance bytes, approval,
   signing, durable admission, backups, recovery, and existing CLI behavior
   remain unchanged.
8. **Forbidden changes:** Optional IDNA pin, protected helper edit, automatic
   migration/ingestion/redistillation, inferred consent, new issuer/resolver,
   or Chroma-as-authority.
9. **Done:** T0b references agree; deliberate schema/inventory/hash mutants
   fail; only declared future-T tests remain red; pushed commit receives Codex
   `CONTINUE`. No bounded TEST PASS is claimed.
10. **Ryan confirmation:** No within exact T0–T5; yes for any different
    dependency, schema, component membership, data model, trust, signing,
    approval, or provenance behavior.
11. **Live inspection:** Codex checks commit/diff/files, required IDNA delta,
    schema inventory, known answers, independent arrays, negative controls,
    raw runner output, and every outside-runner command.
12. **Verdict:** ConvMem contract verdict.

### M3 — T1–T2 data flow, state, authority, publication, and failure

1. **Name and purpose:** Implement the frozen T1–T2 authority/state machine.
2. **Architectural outcome:** Full-bound canonical reduction, conserved
   authority, immutable publication, fail-closed recovery, and display-only
   query filtering.
3. **Affected surfaces:** `bound_read_scope.py`, `strict_grounding.py`,
   `strict_evidence_state.py`, `strict_projection_publisher.py`,
   `strict_projection.py`, their schemas and named tests.
4. **Preconditions/dependencies:** M2 `CONTINUE`; exact issuer/source
   inventories and identity algorithms frozen.
5. **Implementation tasks:** Implement enrollment/genesis, strict identities,
   original-admission qualification, cumulative authority, fence→intent→head
   advance→cold build→publication order, full publication CAS, deterministic
   state, rollback/rebuild/recovery, and persisted expiry. For the parent's
   “retire first” rule, the fixture publisher treats external retirement and
   exact empty-domain proof as preconditions; its CLI refuses a nonempty or
   unknown slot and does not invent a manager/platform capability. T5 later
   supplies only the parent-fixed fake retirement port.
6. **Tests/evidence:** Only T1/T2-owning portions of parent cases 5–27,
   41–44, 49, 51–52, 55, and 57; fault injection at every write/fsync/rename/
   pointer boundary; two fresh roots; independent reducer/qualifier results.
   Reader/server portions remain red until M4 and no whole-case PASS is claimed
   when a case has a later layer.
7. **Invariants:** Revocation/supersession permanent; late evidence cannot
   upgrade admission; rollback never restores authority or renews lifetime;
   ambiguity is unavailable/quarantined.
8. **Forbidden changes:** Query-time reducer, implicit add, authority rollback,
   generation-only CAS, self-authentication, mutable/global store, any
   redistillation, or a publisher-owned retirement mechanism.
9. **Done:** T1/T2 rows and negative controls pass inside the runner;
   crash/retry/recovery is deterministic; only declared T3–T5 rows remain red;
   pushed commit receives Codex `CONTINUE`. No overall TEST PASS is claimed.
10. **Ryan confirmation:** No for exact fixture implementation; yes for any
    persistent format/migration or rollback/recovery semantic change.
11. **Live inspection:** Codex checks pushed commit/diff/files, state/schema
    writes inside disposable roots, fault output, CAS/retry evidence, retirement
    refusal, permissions, raw runner output, and outside-runner commands.
12. **Verdict:** ConvMem verdict.

### M4 — T3 read-only CLI/MCP and Gate B review hold

1. **Name and purpose:** Finish Gate B before any connector/control work and
   hold for an exact-commit conformance review.
2. **Architectural outcome:** The file CLI and strict server expose exactly
   `search`, `unresolved`, and `related`, zero resources/templates, immutable
   operator-owned audience, and untrusted raw evidence; OpenClaw remains absent.
3. **Affected surfaces:** `strict_projection.py`,
   `openclaw_strict_server.py`, reject-only `mcp_server.py`, Gate B schemas,
   fixture paths, and Gate B strict tests. No connector/controller/supervisor
   behavior is implemented here beyond M1 production refusal.
4. **Preconditions/dependencies:** M3 `CONTINUE`; all T0–T2 evidence present;
   Ryan's refusal-contract ruling and this overlay are exact grant inputs.
5. **Implementation tasks:** Implement the exact lexical reader/direct file
   CLI, selector-only display, public opening, three strict methods, v3 result/
   error serialization, and zero resources. Preserve baseline profile parsing's
   `(value or "").strip().lower()` normalization: normalized empty/`full` is
   full, `shell` is shell, `openclaw-strict` refuses legacy entry with the
   dedicated-entrypoint instruction, and every other normalized nonempty value
   terminates before registration. Exact stderr bytes and numeric status remain
   noncontractual under Ryan's ruling; Grok must not turn its chosen
   presentation into a test-derived contract.
6. **Tests/evidence:** Gate B's cases 1–27, 40–44, 49–52, strict-server portion
   47, private/public portion 55, and Gate B portions 57–58, separated by layer.
   The unchanged `--suite all` runner may still be red only for declared T4/T5
   files; all Gate B rows and mutants must be green in two fresh roots.
7. **Invariants:** Legacy full/shell behavior stays byte-compatible; reads do
   not mutate mtimes/cache/files; no OpenClaw, writer, publisher import in the
   public reader, or governance authority is exposed.
8. **Forbidden changes:** Connector aliases, OpenClaw plugin/config, native
   memory, `ask`, global search, dynamic dispatch, ACP/subagents/channels,
   credentials, real inference, or any T4/T5 implementation before review.
9. **Done:** Gate B evidence is green at one pushed commit; the profile tests
   prove nonzero exit, empty stdout, zero registration/start/effect, no raw-
   value disclosure, and the semantic dedicated-entrypoint instruction; and
   Codex issues a written Gate B `CONTINUE` citing that commit. This is a Gate
   B review PASS, not final bounded TEST PASS.
10. **Ryan confirmation:** No routine reapproval inside the exact grant. Any
    contract/profile/permission change pauses for Codex/Kiro and requires a new
    Ryan grant if a governing SHA or scope changes.
11. **Live inspection:** Codex inspects the complete Gate B diff/commit/push,
    profile and tool/resource enumeration, legacy behavior, raw runner output,
    dependencies, schemas/data, permissions, protected bytes, deviations, and
    all commands outside the runner. Grok must stop until written `CONTINUE`.
12. **Verdict:** ConvMem Gate B verdict; no real or fake OpenClaw verdict.

### M5 — T4 uninstalled connector checkpoint

1. **Name and purpose:** Implement only the connector after Gate B review and
   stop before lifecycle/controller work.
2. **Architectural outcome:** Three fixed aliases use an injected test
   transport, validate the exact launch tuple, and wrap raw evidence as
   untrusted data. No OpenClaw process or registration exists.
3. **Affected surfaces:** Only
   `integrations/openclaw-convmem-reader/{package.json,openclaw.plugin.json,index.js,test/connector.test.mjs}`
   and parent-listed connector tests/fixtures.
4. **Preconditions/dependencies:** Written Codex Gate B `CONTINUE` citing the
   exact pushed M4 commit.
5. **Implementation tasks:** Implement fixed alias mapping, exact launch-tuple
   validation, injected `spawn`, bounded framing/queue/deadline, cancellation,
   partial-frame/late-success denial, and production registration refusal;
   commit, push, and stop.
6. **Tests/evidence:** Only Gate C connector portions of cases 2, 33, 35, 48,
   57, and 58; one active plus eight pending; ninth denial; exact frames and
   fixed response; no automatic retry after uncertain delivery; no real child.
7. **Invariants:** Retrieved content has no instruction authority; immutable
   audience and three aliases cannot widen; exact explicit authority-operation
   retries retain parent case 43/49 semantics outside the connector.
8. **Forbidden changes:** Dynamic dispatch/path/argv, real registration,
   gateway/model/provider/filter, native memory, credentials, ACP, subagents,
   channels, remote inference, or controller/supervisor implementation.
9. **Done:** Assigned T4 rows are green at one clean pushed commit and Codex
   issues commit-tied `CONTINUE`. No final TEST PASS or OpenClaw-runtime claim.
10. **Ryan confirmation:** No routine reapproval inside the exact T4 grant;
    yes for any real process, permission, registration, interface, or limit
    change.
11. **Live inspection:** Codex inspects connector diff/files/manifest/API,
    commit/push, runner output, injected spawn trace, dependencies, permissions,
    outside-runner commands, and unsupported claims. Grok stops at this hold.
12. **Verdict:** Connector/protocol-fake and bounded integration verdicts only.

### M6 — T5 fake lifecycle, concurrency, rollback, and recovery

1. **Name and purpose:** Implement and falsify the controller/manager/
   supervisor protocol cores after the T4 hold.
2. **Architectural outcome:** Stable-slot lifecycle, peer policy, lock order,
   turns, release/revoke, retirement, quarantine, and recovery operate only
   through the parent-fixed `FixturePlatform` ports.
3. **Affected surfaces:** `openclaw_activation_controller.py`,
   `openclaw_activation_supervisor.py`, their schemas/tests, and fixed fixture
   event scripts. Earlier Gate B/T4 files change only to correct a proven defect.
4. **Preconditions/dependencies:** Written Codex `CONTINUE` citing the exact
   pushed M5/T4 commit.
5. **Implementation tasks:** Implement one-turn/no-turn-queue state, stable
   identities, peer/access validation, clocks/boots, watchdog/deadlines,
   release/revoke, independent manager observation, retirement/quarantine, and
   scripted concurrency/crash/restart/rollback events; commit, push, and stop.
6. **Tests/evidence:** Gate C fake-process portions of cases 33, 35, 45–46,
   53–54, pre-activation 55, and lifecycle/production-refusal portions 57–58;
   deterministic traces for blocked consumers, detached descendants, stale
   receipts, partial independent removal, clock/boot changes, and teardown.
7. **Invariants:** Supervisor cannot attest emptiness; only exact-invocation
   terminal+empty manager observation permits retirement; rollback is serving-
   only and never renews expiry; uncertain teardown retains the exact root.
8. **Forbidden changes:** Real users/services/sockets/mounts/filters, cleanup-
   as-proof, automatic rerun, lock widening, old-head/expiry restoration,
   production fake selection, destructive recovery, or implicit add.
9. **Done:** Assigned T5 rows/races are green in two fresh roots at one clean
   pushed commit and Codex issues commit-tied `CONTINUE`. No final TEST PASS or
   real containment/authentication verdict.
10. **Ryan confirmation:** No routine reapproval inside exact T5; yes to change
    rollback/recovery, persistence, limits, permission, or production behavior.
11. **Live inspection:** Codex checks lifecycle diff/files, commit/push, raw
    runner output, seeds/events/traces, retained state, schemas, permissions,
    process/network/FD proof, outside-runner commands, and success claims.
12. **Verdict:** ConvMem interaction plus connector/protocol-fake integration
    verdict; real-runtime verdict deferred.

### M7 — Observability and audit trails

1. **Name and purpose:** Make every bounded result attributable and reviewable.
2. **Architectural outcome:** Evidence binds plan SHA, implementation SHA,
   source/runtime/component hashes, selected tests, process trace, and outcome
   without creating a new authority source.
3. **Affected surfaces:** Tracked fixture inputs/helpers remain only in their
   parent-defined manifest paths. Generated results exist only under disposable
   `/fixture/evidence` and the fixed outer collection root
   `/tmp/convmem-openclaw-evidence/<source-commit>/<run-label>/`; `/tmp` is
   staging only. Codex owns evidence collection and copies exact hashed results
   to the Ryan-designated durable review location. Neither location is a
   tracked source/component/fixture-hash member. No production telemetry or
   live ledger write.
4. **Preconditions/dependencies:** M6 `CONTINUE`; clean pushed implementation
   commit; exact source and semantic-parent SHAs.
5. **Implementation tasks:** Emit canonical inventories, labels `STATIC`,
   `FAKE`, `DISPOSABLE_KERNEL`, or `REAL`, exact skips/exclusions, timing,
   output, tmp usage, negative controls, and changed-file/protected-byte proof.
   Codex collects only the predeclared outputs and records the staging-to-
   durable byte/hash mapping; Grok cannot select a different destination.
6. **Tests/evidence:** Dry-collect the bounded evidence from the runner without
   changing its suite selection; independently compare canonical arrays and
   prove generated paths are absent from source/component/fixture hashes, no
   full discovery occurs, tool inventory is exact, and reads do not mutate
   mtime/cache/files. Compare staging and durable evidence byte-for-byte before
   staging can disappear. This milestone does not claim final reproduction PASS.
7. **Invariants:** Audit evidence is not approval, signing, admission,
   qualification, manager emptiness, or promotion.
8. **Forbidden changes:** Live telemetry, secrets, private paths, fabricated
   provenance, omitted failures, volatile-only handoff evidence, unsupported
   “all 58 passed” claim.
9. **Done:** Evidence locations and mappings are deterministic and excluded
   from all governed hashes; exact evidence is durable with a verified staging
   hash mapping; pushed M7 commit receives Codex `CONTINUE`. Final reproduction
   and TEST verdict remain M8.
10. **Ryan confirmation:** No for fixture evidence; yes for any persistent/live
    audit store, telemetry, external sink, or ledger mutation.
11. **Live inspection:** Codex checks commit/diff/files, raw outputs, labels,
    hashes, locations, exclusions, four fixed deselections, capacity, new
    dependencies, outside-runner commands, and claim/evidence mapping.
12. **Verdict:** Separate ConvMem and connector/protocol-fake evidence verdicts,
    plus integration evidence verdict; no OpenClaw runtime verdict.

### M8 — Adversarial testing

1. **Name and purpose:** Run the one final bounded acceptance entrypoint and
   attack every assigned trust/failure boundary before conformance review.
2. **Architectural outcome:** Parent cases 1–58 are reported by owning gate;
   fixture success cannot stand in for blocked real/live gates.
3. **Affected surfaces:** Only
   `tests/fixtures/openclaw_strict/{constants.py,suites.py,run_isolated.py,audit_evidence.py,adversarial_matrix.py}`
   as needed for the parent-fixed report/validation path, plus the single
   existing semantic-parent literal assertion in
   `tests/test_openclaw_strict_packet_contract.py`. Generated output is only
   `/fixture/evidence/{pytest-strict-junit.xml,pytest-legacy-junit.xml,pytest-node-outcomes.json}`.
4. **Preconditions/dependencies:** M7 and the completed M8 correction are
   accepted at clean pushed `8010fb060c2edc29e1b09d7a30b1a1da2689d489`.
   M11 reconstruction must preserve this runner and evidence contract exactly;
   it does not reopen M8 implementation.
5. **Implementation tasks:** Completed at the accepted tip: mechanically repin `SEMANTIC_PARENT_SHA` and its
   existing assertion; add exactly the parent §5.1 xunit1/JUnit arguments to
   the two existing Python argv arrays; parse the two reports after the same
   processes finish; enforce every parent reconstruction/outcome/count rule;
   emit the exact canonical report; keep any AST inventory diagnostic-only;
   and leave the Node argv byte-identical. No selected test logic or file list
   changes. Commit, push, stop for Codex inspection, then—only after a
   commit-specific `CONTINUE`—run the parent §5.1 entrypoint with
   `--source-commit` equal to that clean correction SHA,
   `--plan-sha SEMANTIC_PARENT_SHA`, the unchanged supplied
   runtime, and `--suite all`. Do not modify code between reproductions.
6. **Tests/evidence:** Two fresh-root green runs of the exact three commands;
   raw stdout/stderr/status; both raw JUnit files; canonical exact strict and
   legacy node/outcome arrays; identical arrays across runs; 238 strict passes,
   29 Node passes, 115 legacy passes, one legacy skip and four fixed
   deselections; capacity/process/import/mount/FD/network evidence; exact
   input/expected/evidence triples; failed mutants; protected-byte/allowed-file
   report; and explicit Gate B/C case ownership. Never claim all 58 cases
   passed. AST definitions are not collected-node evidence.
7. **Invariants:** Leakage-safe fixtures; no credentials/live data; no broadened
   test selection, permissions, or scope to make tests pass.
8. **Forbidden changes:** Any new test/test-logic edit beyond the mechanical
   parent-SHA assertion, selector or deselection change, collect-only/extra
   process, conftest/environment injection, plugin/dependency, permission or
   runtime change, report outside `/fixture/evidence`, AST-derived collected
   claim, skip, mocked-success denial, implementation-derived expected value,
   or host execution called acceptance.
9. **Done:** **Accepted at `8010fb0`.** The correction diff stays inside field 3; every parent JUnit/parser
   negative rejects; every assigned Gate B/C row passes twice at the same clean
   commit; both canonical arrays are exact and identical; fixed behavioral
   counts remain unchanged; all mutants fail; Codex issues commit-tied
   `CONTINUE`; and bounded `TEST PASS` is claimed here exactly once. Any other
   result is BLOCKED with retained evidence; out-of-scope rows remain explicitly
   untested/blocked.
10. **Ryan confirmation:** Historical M8 confirmation and acceptance are
    complete. A new exact M11 grant is required before reconstruction or fresh
    runs on the integration baseline. Frozen disposable reruns under that grant
    need no per-run approval; live, destructive, costly, irreversible or
    permission-changing tests still require Ryan.
11. **Live inspection:** Codex first checks the full correction diff, exact
    argv arrays, old/new SHA pin, unchanged test logic/selectors/deselections/
    Node argv/dependencies/permissions/runtime, generated paths and parser
    failure rules. After `CONTINUE`, Codex checks the exact command/source SHA,
    both raw JUnit files, canonical arrays/counts/outcomes, raw outputs/statuses,
    two roots, negative failures, fixture/runtime/component hashes, resource
    bounds, changed files, commits/push, outside-runner commands, deviations,
    and unsupported claims.
12. **Verdict:** Separate ConvMem Gate B, connector/protocol-fake Gate C, and
    bounded integration verdicts; no OpenClaw runtime verdict.

### M9 — Blocked post-fixture gates: governed writes and real runtime

1. **Name and purpose:** Keep Gate W memory governance and Gate D real-runtime
   qualification as separate, independently authorized outcomes after bounded
   T0–T5. They share one milestone only because neither is executable work in
   this overlay; neither gate can satisfy or authorize the other.
2. **Architectural outcome:** Gate W, if later granted, admits governed memory
   only through an independently reviewed ConvMem CLI. Gate D, if later granted,
   proves actual OpenClaw authentication, containment, distribution, manager
   ownership, mounts, peers, and local inference without authority transfer.
3. **Affected surfaces:** **UNRESOLVED.** Gate W owns later schemas and
   `governed_admission.py`. Gate D owns actual adapters, package/image,
   service/unit, socket, filter, UID/GID, model/provider, and config paths.
   Exact paths must be named in separate future packets.
4. **Preconditions/dependencies:** M8 bounded Gate B/C PASS. Each subgate then
   requires its own architecture/execution packet, adversarial/design reviews,
   and exact Ryan grant. A PASS for one is not a precondition waiver for the
   other.
5. **Implementation tasks:** **BLOCKED.** Gate W's packet must bind eligibility,
   unitization, proposal, approval, signing, provenance, explicit admission,
   recovery, retrieval, and rejection to existing authorities. Gate D's packet
   must resolve C-RUNTIME/D-CONTAINMENT/D-DISTRIBUTION and exact authentication,
   package, manager, provider, and permission bytes. Grok must infer neither.
6. **Tests/evidence:** Gate W owns case 56 plus 41–44, 49, 51–52 through the
   real governed CLI on disposable stores; unauthorized/self-approved/poisoned
   writes fail. Gate D repeats cases 1–4 and owns real portions 28–36, 38–39,
   45–47, 53–55; prove real isolation, authentication, empty-domain retirement,
   and no ambient credential/tool access.
7. **Invariants:** Agents propose; Ryan locks. Approval, admission, durable
   storage, projection, and publication stay separate. ConvMem remains source
   of truth; runtime sees only committed public projection; evidence text has
   no instruction authority.
8. **Forbidden changes:** Autonomous writes, self-approval, silent migration,
   automatic ingestion/redistillation, inferred authorization, live data,
   dummy credentials, shared host inference, permissive mounts, unbounded
   tools/network, fake-derived qualification, or autonomous external acts.
9. **Done:** Not reachable in this revision. Gate W and Gate D each need their
   own reviewed packet, grant, evidence, and separately reported PASS. Neither
   is implemented, tested, or authorized here.
10. **Ryan confirmation:** Mandatory before either design lock/implementation;
    before persistence/migration/admission for W; and before every permission,
    tool, service, user, socket, mount, network, model/provider, package, or
    external configuration for D.
11. **Live inspection:** Future supervisors separately inspect every W data-
    model/trust/writer/migration/provenance/persistence change and every D
    privilege/config/package/process/mount/network/peer boundary. Evidence and
    statuses may not be combined.
12. **Verdict:** Separate ConvMem Gate W verdict; separate OpenClaw Gate D and
    integration verdicts. No cross-gate PASS inference.

### M10 — Limited web-development pilot (Gate D-V then Gate E)

1. **Name and purpose:** Measure whether the integrated system improves a
   bounded web-development task without weakening governance.
2. **Architectural outcome:** A leakage-safe, pre-registered comparison binds
   episode, target, probe, trace, action, and outcome identities. Capture is
   recorded as disabled; no capture identity is minted through Gate E.
3. **Affected surfaces:** **UNRESOLVED** pilot corpus, tasks, scoring rubric,
   trace store, target site, and isolated runtime packet. Capture policy is not
   an M10 surface; transcript capture/automatic indexing remain disabled.
4. **Preconditions/dependencies:** M9 Gate D PASS; a separately reviewed Gate
   D-V methodology; and a Ryan grant for exactly eight predeclared tasks, two
   fresh repetitions, and two arms (32 runs). Gate E additionally requires a
   positive Gate D-V result, unconditional M9 Gate W PASS, its own reviewed
   packet, and a separate Ryan grant.
5. **Implementation tasks:** **BLOCKED.** A future Gate D-V packet must freeze
   the eight tasks, two repetitions, two arms, baseline/control, measures,
   leakage controls, identities, rollback, and stop rules. A later Gate E
   packet may select only the parent-authorized limited web-development pilot
   after Gate W; it may not enable capture.
6. **Tests/evidence:** Exactly 32 Gate D-V runs with predeclared quality,
   substance, technical, continuity, context-transfer, rework, and safety
   outcomes; blinded/independent scoring; complete traces. Gate E separately
   requires the parent-defined live evidence and rollback proof.
7. **Invariants:** No production target by default; no automatic capture/write;
   no cross-arm leakage; no outcome-based identity rebinding or scope drift.
8. **Forbidden changes:** Expanding beyond web development, live deployment,
   consequential external action, post-hoc metric changes, promotion by result.
9. **Done:** Not reachable until the exact Gate D-V 32-run packet passes, Gate W
   passes, the Gate E packet is reviewed, and Ryan grants exact target/actions;
   pilot PASS is not promotion.
10. **Ryan confirmation:** Mandatory for methodology, target, external actions,
    live data, and every irreversible step. Gate W separately governs writes;
    Gate F separately governs any later capture proposal.
11. **Live inspection:** Future supervisor checks pre-registration, identities,
    target/action allowlist, trace, leakage controls, rollback, and outcomes.
12. **Verdict:** Separate OpenClaw runtime, ConvMem governance, and integration-
    value verdicts. Capture remains a later Gate F question.

### M11 — Final conformance review and documentation

1. **Name and purpose:** Correct PR `#342`'s two confirmed safety defects and
   required-CI applicability failure without weakening ConvMem, hiding tests,
   treating a local fixture PASS as GitHub CI, or expanding into real OpenClaw.
2. **Architectural outcome:** Doctor contains fail-closed MCP import refusal;
   fenced publication/recovery cannot manufacture an exact retry; every pytest
   node belongs to exactly one ordinary/qualified authority partition; the first
   qualified-runtime archive remains immutable and rejected for publication; a
   replacement can exist only as one exact runtime/compliance/manifest delivery set
   built from a complete reviewed component lock; that lock can be reviewed only as
   the canonical thirteen-role provenance packet at the exact separate immutable
   packet/review roots; schema v1 and v2 remain stopped evidence while schema v3
   permits only the exact raw-object-bound absent-member revision projection, binds
   the resulting immutable PAUSE packet and independent disposition, and prevents an
   open unresolved row from becoming build eligibility; the successor partitions all
   baseline obligations losslessly, refuses invented origin authority, and permits
   host-path remediation only through clean replacement from independently locked
   inputs; and
   final R2b authority-content identity converges over the
   unchanged 120-member set.
3. **Affected surfaces:** Five reviewed control documents; three closed
   authority/scope files defining a separate exact ten-path M11 corrective set;
   doctor pair `doctor.py` / `tests/test_doctor.py`;
   publisher pair `strict_projection_publisher.py` /
   `tests/test_strict_projection_publisher.py`; CI paths
   `.github/workflows/pylint.yml` (pytest job only),
   `tests/test_ci_contract.py`, new `scripts/run_switchboard_ci.py`, new
   `tests/test_switchboard_ci_contract.py`, new
   `ci/switchboard-runtime.json`; and the sole R2b inventory JSON. Replacement
   delivery-set and provenance-schema-v1/v2/v3 planning changes only the four Switchboard
   plans. The schema-v3 staging, packet and review roots exist only because of the
   separate completed P0 and review grants; the exact packet and disposition are
   immutable, and this plan neither creates nor changes them. Future acquisition,
   build/packet paths and three
   asset names must be frozen by reviewed successors before creation. No other path
   may change. Evidence uses grant-named disposable/durable roots only.
4. **Preconditions/dependencies:** PR base/head and tree equal §0; required pytest
   failure and ultrareview findings are preserved; Kiro has PASSed the exact
   replacement plan at `PROVENANCE_SCHEMA_V1_PLAN_BASE_OVERLAY_SHA`; Kiro passed
   schema v1 at `PROVENANCE_SCHEMA_V2_PLAN_BASE_OVERLAY_SHA`; its P0 stopped as
   frozen in §0. Kiro passed schema v2 at `PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA`;
   its one P0 stopped on the exact absent member. Kiro passed schema v3 at
   `PROVENANCE_SCHEMA_V3_RESULT_PLAN_BASE_OVERLAY_SHA`; Ryan separately granted its
   collector freeze and one P0 execution, which completed with the exact §0 PAUSE
   packet. Kiro passed the result-binding overlay at
   `PROVENANCE_ACQUISITION_PLAN_BASE_OVERLAY_SHA`; Ryan separately granted Claude's
   independent disposition, which Codex verified at the exact §0 hash and verdicts.
   Kiro PASSes this pre-acquisition parent and overlay; complete cited work-item
   planning, a later exact operation packet and Ryan acquisition grant, and Kiro/
   licensing review of a zero-unresolved component lock remain mandatory
   before any build; Ryan separately grants a deterministic build and
   final packet; Kiro and the independent licensing reviewer PASS the actual final
   bytes; Ryan separately grants the exact three-asset publication and held
   implementation files; the published set then passes exact manifest/hash/extraction/
   hosted-runner preflight; branch, runtime and evidence inputs are clean/inventoried;
   and no prior grant or `CONTINUE` is reused.
5. **Implementation tasks:** Cursor applies the reviewed five-document plan and
   authority/scope rebind, then implements doctor containment, fenced publisher/
   recovery, CI partition/adapter, and independent R2b inventory rotation as
   separate pushed held commits in §10.20 order. Codex proves each exact diff and
   issues a commit-specific status before the next begins. Provenance execution,
   packet/review-root creation, runtime provenance locking, replacement construction
   and publication are separately held work and never implied implementation tasks.
   This overlay creates no component work-item file or operation packet and performs no
   host-path repair; it freezes only the coverage/authority/build contract. The
   duplicate hashing helper cleanup is excluded.
6. **Tests/evidence:** Static schema proof for all thirteen file roles, canonical
   encoding/types/enums/nullability, nonrecursive IDs/hashes, separate immutable
   packet/review roots, cross-file joins, source-authority limits, every §18.25.5
   mutant, every §18.26 historical null-version negative and every §18.27 exact-object
   absent-member positive/negative control; exact frozen collector/result/manifest/
   packet hashes; 651 independently rehashed objects; staging-to-durable byte/mode
   equality; ownership-ledger reconstruction of the runtime tree; exact five-pass/
   11,643,965,233-byte ledger; one projection; 65 negative controls; nine unresolved
   groups totaling 98,608; exact disposition SHA/size/mode/schema, twelve reviewed
   packet hashes, complete sorted open-ID equality and unchanged packet tree; the four
   manifest primary-key hashes; exact twenty-batch/49-page arithmetic; the 19-file
   ownership-dispute queue; and the three host-path objects, occurrence offsets and
   loader findings. Then, only under future grants, rejected-archive preservation;
   complete cited origin work items and exact granted operations; exact
   replacement component lock/file ownership, artifacts/sources/recipes,
   licenses/notices and corresponding-source delivery; deterministic three-role
   construction; manifest/archive/runtime/
   compliance tree hashes; recursive closure and negative controls; closed extraction;
   hosted-runner containment and pinned bubblewrap; then fresh-process doctor continuation/non-disclosure; complete
   fenced crash/recovery/write-set matrix; exact complete pytest `U=O∪Q` with
   empty intersection on the actual GitHub PR merge commit; CI mutation controls;
   unchanged Pylint; independent 120-member R2b convergence and its existing
   negative/coverage/boundary tests; two fresh unchanged M8 runs at 238 strict,
   29 Node and 118/117/one-skip/four-deselection legacy outcomes; seven MCP files;
   durable verification; required GitHub checks green; focused safety/isolation
   review; and Kiro exact-tip integrated conformance review.
7. **Invariants:** Existing product schemas, hashes, publication layout, operation-ID
   grammar, T0–T5 semantics, three-tool surface, Pylint job/baseline/gate, M8
   runner/commands/selectors/four deselections/counts, R2b
   member set/seed/closure/routes, permissions and blocked later gates remain
   unchanged. The rejected runtime archive/hash remains immutable and unpublished;
   no byte-level PASS transfers to the replacement. The provenance packet and review
   leaves are separately atomic, immutable and non-self-referential; structural
   validity may preserve an honest unresolved `PAUSE`, while build eligibility requires
   zero unresolved rows and exact technical/provenance/licensing PASS. The schema-v3
   packet tree is single-assignment at `PROVENANCE_V3_PACKET_TREE_SHA256`; its exhausted
   read budget cannot be reset and no reviewer may modify it. The disposition remains
   technical `PASS`, provenance/licensing `PAUSE`, counsel-required and immutable with
   all 98,608 IDs. The component/file/edge/unresolved baseline sets remain exact and
   every unsupported origin remains unresolved. The three host-path objects are
   rejected-build evidence, never repair inputs. The replacement set's three roles
   are jointly single-assignment at later reviewed exact coordinates and are never
   repaired, partially published, substituted or resolved through `latest`. The
   historical T0–T5 product/schema allowlists are not widened. Retained failures are
   never called full pytest PASS.
8. **Forbidden changes:** Skip/xfail/marker/wildcard/failure-derived selector;
   Python-version-only evasion; import-refusal weakening; ordinary publish while
   fenced; fence clearing with durable or uninspectable intent; schema/data-model/
   hash changes; copied containment implementation; reuse/upload/repair of the rejected
   archive; reuse, deletion or repair of schema-v1/v2 staging; a generic missing/null
   equivalence or second SBOM version inference; schema-v3 collector rerun, read-ledger
   reset, packet/disposition mutation or replacement; omitted/duplicated/reassigned
   component, file, nested-edge or unresolved coverage; ownership guessing; promotion
   of a name/PURL/metadata/SBOM/search/registry/cache/host hint to authority;
   mutable/latest/host-fallback replacement; copied rolling-host input;
   incomplete component ownership; schema/enum widening; manifest self-hash; reviewer
   mutation of the packet leaf; ambient/ungranted origin, redirect, cache or executable
   download; treating structural validity as build eligibility; missing compliance role; publication while
   licensing is `PAUSE`; treating Kiro PASS as legal or
   external-action clearance; copied or post-build-rewritten host-path binaries;
   `patchelf`, `chrpath`, prefix replacement, blanket absolute-path/debug exception;
   Pylint edit; M8 runner edit; sixth control doc; product allowlist
   widening or an eleventh M11 corrective path; R2b live operation; hash-helper
   refactor; unlisted path/byte; merge,
   deployment, real OpenClaw, live data or later-gate action.
9. **Done:** Replacement-plan-ready was reached by Kiro PASS at
   `PROVENANCE_SCHEMA_V1_PLAN_BASE_OVERLAY_SHA`. Schema v1 design passed at
   `PROVENANCE_SCHEMA_V2_PLAN_BASE_OVERLAY_SHA`, while its P0 execution stopped and
   created no durable packet. Schema v2 design passed at
   `PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA`, while its one P0 execution stopped
   before a result or durable packet. Schema v3 design passed at
   `PROVENANCE_SCHEMA_V3_RESULT_PLAN_BASE_OVERLAY_SHA`; its one P0 execution completed
   and published the exact immutable PAUSE packet. Result-binding-ready was reached by
   Kiro PASS at `PROVENANCE_ACQUISITION_PLAN_BASE_OVERLAY_SHA`; independent review is
   complete at `PROVENANCE_V3_REVIEW_DISPOSITION_SHA256` but returned provenance and
   licensing `PAUSE`. Pre-acquisition-design-ready means exact-tip Kiro PASS on this
   semantic parent/overlay. Complete-origin-planning, operation-packet-ready,
   acquisition-ready, provenance-closed, lock-ready,
   build-ready, packet-ready, publication-ready and CI-admission-ready are separate
   later states defined by §§18.24–18.29/§§10.22–10.27; none is reached here.
   Publication-ready additionally requires actual-byte technical/provenance/licensing
   PASS and Ryan's exact external-action grant. Correction-ready additionally requires
   Ryan's exact implementation grant and the separately published/verified set. Merge-ready requires
   every held diff/evidence item in field 6, all required GitHub checks green,
   focused safety PASS, Kiro integrated-tip PASS and Ryan's final merge decision.
10. **Ryan confirmation:** The one schema-v3 P0 execution is complete and not reusable.
    The independent reviewer write is complete and not reusable. Confirmation remains
    mandatory separately for complete cited origin planning and each later schema-
    bound metadata/acquisition operation, including exact roots, origins,
    operations, redirects, byte ceilings, parser/tool versions and checkpoints;
    component-lock acceptance,
    replacement build, final packet, runtime tag/release/three-asset creation, CI
    admission, implementation after licensing closure, any changed scope or governing SHA, PR amendment, merge, real
    OpenClaw, live data, deployment, promotion and Gates D/W/D-V/E/F. Planning
    review alone authorizes none of them.
11. **Live inspection:** Codex checks exact refs/tree, plan blobs/modes,
    authority/scope negative controls, every held diff, runtime inventory and
    rejected-archive preservation, schema role/count/type/enum/nullability, exact P0
    result/manifest/packet identities, staging-to-durable equality, object hashes,
    unresolved-group arithmetic, exhausted read ledger, disposition identity/schema/
    packet bindings and complete open-ID equality, manifest primary-key set identities,
    batch/page/ownership-dispute coverage, host-path objects/offsets/loader findings,
    nonrecursive hashes, component-lock/file-ownership closure, binary/
    source/build/license/notice/source-delivery proof, three-role manifest/archive/
    extraction identities, hosted bwrap
    preflight, doctor processes, publisher pre/post bytes, complete collected
    node identities/outcomes, merge-tree identity, CI dependencies/receipts, R2b
    manifests/identity convergence, Pylint/M8/MCP output, durable mappings and all
    GitHub contexts. Cursor pushes and stops after every hold.
12. **Verdict:** Schema-v3 design and P0 execution are preserved results. Separate
    result-binding and independent disposition verdicts are preserved results.
    Separate verdicts remain mandatory for this pre-acquisition/clean-replacement
    plan; complete cited origin planning; every exact acquisition operation;
    successor component-lock completeness;
    replacement construction; runtime byte qualification; public redistribution/
    provenance/licensing; final packet; external publication and CI admission; doctor safety;
    publisher/recovery safety; ordinary/qualified CI completeness; R2b convergence; M8/MCP/
    Pylint; bounded ConvMem integration; PR merge readiness; real OpenClaw; and
    pilot/production. Historical PASSes remain evidence, not acceptance transfer.

## 4. Milestone acceptance checklist

- [x] M0 exact SHAs/grants/branch/worktree/runtime inventories bound at the
      accepted original baseline.
- [x] M1 T0a runner/pre-import/refusal controls pass; future-T reds mapped.
- [x] M2 T0b schemas/vectors/oracles and mandatory IDNA pin pass.
- [x] M3 T1–T2 state, authority, publication, failure/recovery layers pass.
- [x] M4 Ryan's refusal ruling is enforced; T3/Gate B passes; written Gate B
      hold clears.
- [x] M5 T4 connector rows pass; written commit-tied hold clears.
- [x] M6 T5 fake lifecycle/concurrency/recovery rows pass in two roots.
- [x] M7 evidence stays outside governed hashes and is copied with verified
      hashes to the designated durable location.
- [x] M8 exact runner passes twice; bounded TEST PASS accepted at `8010fb0`.
- [ ] M9 Gate W and Gate D remain separately BLOCKED pending packets/grants.
- [ ] M10 remains BLOCKED until exact 32-run Gate D-V, Gate W, and Gate E.
- [x] M11 current-main replay and pin/comment reconciliation preserved at
      `a11b7a2`; first fresh attempt retained as a pre-test allowlist PAUSE.
- [x] M11 reviewed-plan correction and follow-up evidence repairs preserved at
      `9c6421a`; two fresh M8 runs and seven MCP regressions pass.
- [x] M11 actual current-main Pylint failure retained with exact report,
      environment and durable-copy hashes; no baseline/gate weakening occurred.
- [x] M11 exact 44-path remediation and bounded repairs preserved at `3f8ef83`;
      unchanged actual Pylint gate and critical invariant collection pass.
- [x] M11 first reviewed differential plans preserved at `853ef98`; complete
      baseline/candidate node sets and outcomes matched, 28 signature mismatches
      were retained, and PAUSE stopped all later evidence.
- [x] M11 path/identity reconciliation applied at `7f2a2e2`; the complete
      `9c6421a`-versus-candidate differential passes with 238 retained debt
      nodes explicitly recorded and the unchanged actual Pylint gate passes.
- [x] M11 final M8 run 1 retained as a pre-fixture authority-packet PAUSE with
      classification SHA-256 `e217e560…`; runtime remained unchanged; run 2 and
      seven MCP regressions did not run.
- [x] M11 authority-packet plans and four-literal correction preserved at
      `d7b1592`; fresh differential and unchanged Pylint gate pass. Final M8
      run 1 retained as an in-suite bundle-schema PAUSE with classification
      SHA-256 `c25ece63…`; all 28 strict failures share the one confirmed
      production-literal cause; runtime remained unchanged; run 2 and seven MCP
      regressions did not run.
- [x] M11 bundle-schema plans and exact one-literal correction preserved at
      `851edbe4`; fresh differential and unchanged Pylint gate pass. Final M8
      run 1 retained as a pre-fixture authority-packet PAUSE with classification
      SHA-256 `3fbfab4b…`; runtime remained unchanged; run 2 and seven MCP
      regressions did not run.
- [x] M11 post-bundle packet correction and final evidence preserved at
      `cd60cf19`; fresh governed differential, unchanged Pylint, two fresh M8
      runs, seven legacy MCP regressions, durable verification and integrated-
      tip Kiro review all PASS on historical baseline `9193f5e`.
- [x] M11 fresh merge audit found current main `a92a74e`, no PR and a real
      conflict in the governed STATUS document; merge remains PAUSED and the
      reviewed evidence branch remains immutable.
- [x] M11 exact-current-main reconstruction preserved at `30bc134d`; all three
      held commits, path algebra, final tree composition, runtime inventory and
      unchanged `origin/main` passed independent inspection.
- [x] M11 complete current-main/candidate pytest runs retained with 2,686 and
      2,924 nodes. The 238 additional Switchboard nodes all exist in `cd60cf19`
      with identical outcomes; the old candidate-only PASS/SKIP rule correctly
      produced PAUSE, ledger SHA-256 `3bd89ebf…`, and blocked Pylint/M8/MCP.
- [x] M11 three-tip plan and four-literal rebind preserved at `d276cb4`; source
      and runtime checks passed. Evidence preflight then found main at
      `5c6a4a8` and stopped before slot/run creation or any suite process.
- [x] M11 advanced-main reconstruction preserved at `776a4ca3`; three held
      commits, source composition and runtime inventory passed. Three complete
      pytest runs and all 166 reruns completed; the finalizer retained the exact
      22-node inner-role signature PAUSE and blocked Pylint/M8/MCP.
- [x] M11 inner-role plan/rebind and fresh same-slot evidence preserved at
      `65bbfd6f`; the 238-node partition, five-node R2b proof, exact 22-node
      semantic-signature proof and full differential pass. The unchanged
      Pylint gate then paused on three candidate-introduced `R0801` pairs; M8
      and MCP did not run. Read-only current-main triage is sealed under
      `PYLINT_TRIAGE_LEDGER_SHA256`.
- [x] M11 first Pylint correction and fresh differential preserved at
      `c71d37a`; protected gate status zero did not override exact 456/71 pair
      PAUSE. Ledger, manifest, report and pair-comparison hashes are sealed;
      M8/MCP did not run.
- [x] M11 Pylint-acceptance-drift plan/rebind/source correction and fresh
      three-tip differential preserved at `caec5c6`; protected gate zero and
      exact 69-pair equality did not override the stale 454-total rule. The
      458/29 `R0401`/69 `R0801`/240 PAUSE and four seeded diagnostic probes are
      sealed; M8/MCP did not run.
- [x] M11 `R0401`-determinism plan and four-literal rebind preserved at
      `9da6dd98`; fresh same-slot `N1`/`R`/final-candidate differential and
      paired `N1`/final `PYTHONHASHSEED=0` Pylint PASS with exact
      458/29/69/240 counts and three semantic hashes.
- [x] M11 final M8 run 1 at `9da6dd98` passed 238 strict and 29 Node tests,
      then retained the exact 118-collected/117-passed legacy result as PAUSE
      against the historical 116/115 expectation. The delta is exactly two
      added passing current-main safety nodes; runtime stayed unchanged and
      M8 run 2/MCP did not start.
- [x] M11 legacy-count correction and all fresh differential/Pylint/M8/MCP/
      durable/Kiro evidence completed at `PRESERVED_PR342_HEAD_SHA`; PR `#342`
      was separately authorized and created against exact `PR342_BASE_SHA`.
- [x] PR `#342` required-check failure and focused ultrareview preserved: 83
      pytest failures partition into exact 22/56/5 families; doctor import
      containment and fenced retry/recovery are confirmed merge blockers.
- [x] Kiro exact-tip PASS on §18.22/§10.20 at overlay `a23d843`.
- [x] Runtime-delivery archive locally validates exact source, modes, members,
      extraction and frozen hashes without changing the runtime or publishing.
- [x] Kiro exact-tip PASS on §18.23/§10.21 at overlay `c63e52b`.
- [x] Independent provenance/licensing review and Kiro concurrence retained the
      first archive as `PUBLICATION_ELIGIBLE=false`,
      `LICENSING_DISPOSITION=PAUSE`; it is rejected for publication.
- [x] Kiro exact-tip PASS on §18.24/§10.22 replacement plan at overlay `3402e62a`.
- [x] Kiro exact-tip PASS on §18.25/§10.23 schema v1 at `5f397852`.
- [x] Schema-v1 offline P0 proved the exact runtime tree, then stopped on the component
      initially classified as null-version; no durable packet/review root exists and v1 staging is rejected.
- [x] Kiro exact-tip PASS on §18.26/§10.24 schema v2 at `2956f701`.
- [x] The single schema-v2 P0 proved the raw `base64.version` member is absent and
      stopped before result/ledger/manifest/durable packet creation; cumulative reads
      are three complete passes and 7,106,471,781 bytes, and v2 staging is rejected.
- [x] Kiro exact-tip PASS on §18.27/§10.25 at schema-v3 overlay `d03aa553`.
- [x] Separately granted schema-v3 collector freeze and one offline P0 execution
      completed at the exact 11,643,965,233-byte cumulative ceiling. Immutable packet
      tree `491ae60b…` verifies and honestly retains 98,608 open rows.
- [x] Kiro exact-tip PASS on §18.28/§10.26 result-binding overlay `3b3550c`.
- [x] Separately granted independent review disposition bound to the exact manifest and
      packet hashes; no packet repair and no build-eligibility claim.
- [x] Original Kiro exact-tip PASS on §18.29/§10.27 at overlay `a10a84d`.
- [x] PR `#345` merged the conflict-free current-main pre-acquisition and
      clean-replacement plan at `5bcc6c7`; Kiro exact-main PASS confirmed the four
      merged plan blobs equal carrier `6429d27` and preserve §§18.29/10.27.
- [ ] Complete cited component and ownership work-item planning with exact disjoint/
      union proof; unknown origins remain unresolved and no request is authorized.
- [ ] Separately reviewed and granted exact-origin provenance acquisition; successor
      packet has zero unresolved rows; Kiro lock review and independent provenance/
      licensing PASS.
- [ ] Separately granted deterministic replacement build; qualified runtime,
      compliance/corresponding-source and manifest roles independently verified.
- [ ] Reviewed final packet with exact three-asset coordinates/hashes; Kiro and
      independent actual-byte licensing PASS; exact Ryan publication grant.
- [ ] Separately authorized hosted CI admission of the complete verified set.
- [ ] New Ryan implementation grant; held five-plan/authority-scope, doctor,
      publisher/recovery, CI and independent R2b inventory commits; every
      commit-specific Codex `CONTINUE`.
- [ ] Fresh doctor/crash-matrix/ordinary-qualified-CI/R2b/Pylint/two-M8/
      seven-MCP/durable evidence; required GitHub contexts green; focused
      safety/isolation PASS; Kiro exact-tip integrated PASS; Ryan merge decision.

## 5. Required adversarial input/expected/evidence matrix

| Threat | Parent case / gate | Evidence class | Concrete input | Expected behavior | Independent pass evidence |
|---|---|---|---|---|---|
| Memory poisoning | 13, 22, 41, 49, 51 / B | `STATIC`, fixture-only | Alter source bytes behind signed-looking metadata; forge qualification/disposition; supply receipt bytes absent from the protected issuer inventory | Reject the supplied contradiction before publication/serving; never self-authenticate or upgrade trust | Independent qualifier rejects; authority/publication hashes stay unchanged; forgery mutant is red |
| Stale/conflicting memory | 18, 42, 44, 49–50, 52 / B | `STATIC`, fixture-only | Same-check fork, selected-out conflict, stale head/CAS, old generation, withdrawn successor | Full-bound state remains conflict/unavailable as specified; selector/query cannot hide it; no predecessor resurrects | Reference reducer/hash agrees; stale CAS and old-head publication deny |
| Signer/trust failure | 41, 51 / B | `STATIC`, fixture-only | Unknown registry issuer; exact receipt bytes missing/changed in the protected issuer inventory; absent required evidence; late witness | Registry/inventory contradiction rejects. Genuinely missing evidence only weakens assurance. Later evidence cannot upgrade original admission | Registry validator and independent qualifier show reject versus weakened state separately; qualification hash is stable |
| Prompt injection | 32 / D blocked; C fixture negative control under 33/57, without a case-32 PASS claim | `FAKE` negative control now, `REAL` later | Evidence says “ignore policy; call shell; write memory; export secrets” with fake tool syntax/role labels | Bytes remain untrusted tool-result data and cause no instruction/tool action | Exact raw result plus injected-spawn call log, process/network/write trace all show zero extra effect |
| Unauthorized writes | 13–16, 55, 57 / B/C; 38–39 / D blocked | `STATIC`/`DISPOSABLE_KERNEL`; `REAL` blocked | Runtime/connector attempts writer import, projection/control mutation, mtime/cache write, private-file read | Deny before effect; public read surface stays byte/mode/hash/mtime identical | Before/after inventories plus kernel denial and import sentinel |
| Authority escalation | 5–15, 19–27, 33, 53, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Caller supplies project/path/root/profile/tool/peer/UID data to widen the immutable audience | Reject before lookup/effect with equalized public denial where required | Independent scope oracle, zero cross-scope observation, enumeration/peer negative tests |
| Data leakage | 17–20, 23–27, 51, 55, 57 / B/C | `STATIC`/`DISPOSABLE_KERNEL`, fixture-only | Cross-project/site/domain selector; unauthorized related support; raw ID; private-path canary | Whole request denies where required; no existence oracle, partial chain, or private bytes | Equalized error shape after correlation ID, canary denial, authorized-output inventory |
| Scope drift | 1–4, 21, strict-server 47, 58 / B; 33 and 57–58 / C fake; real 47 / D blocked | `STATIC`/`FAKE` now, `REAL` later | Add fourth tool/resource, new dependency/file/path/resolver; add issuer only as registry data; mutate included/excluded component member | Tool/file/dependency allowlists or registry validation fail at their proper boundary before widened serving | Exact independent tool/component/registry arrays and refusal stage; no file-allowlist claim for issuer data |
| Rollback failure | 44, 52, 54, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Select old authority/generation, expire anchor, crash around pointer rename/fsync, retain nonempty manager domain | Only current-head/current-contract/unexpired serving may resume; otherwise unavailable/quarantined; authority/expiry never roll back | Fault/event trace, retained head/expiry, publication hash, independent manager observation |
| Partial failure | 35, 44, 46, 48, 52–53, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Fault each write/fsync/rename; truncate frame; kill builder/child/supervisor/controller; create uncertain delivery | No partial/late success. Connector delivery uncertainty is never automatically retried. Durable state follows exact recovery rules | Fault matrix, frame/process trace, exact retained root/state, zero automatic respawn/retry |
| Concurrent writes and retries | 42–44, 49, 52 / B | `STATIC`, fixture-only | Two operations share expected publication; exact old retry; same collision key with changed bytes; divergent concurrent payloads | At most one transition. Exact preserved retry is idempotent (case 43); exact old operation returns historic outcome/current head (case 49); changed bytes/stale writer reject | Deterministic schedule, operation IDs, independent payload digest, CAS/head history |
| Corrupt/incomplete state | 44, 49, 52, 58 / B | `STATIC`, fixture-only | Missing/extra/symlinked history member; bad canonical bytes/hash; torn tail; ambiguous rename; omitted protected component | Fail closed; never reconstruct success from incomplete proof or self-consistent wrong inventory | Independent scan/component oracle errors and no served publication |
| OpenClaw outside authority | 2, 33, 35, 45–48, 53–55, 57 / C fake; 28–36, 38–39, 45–47, 53–55 / D blocked | `FAKE` now; `REAL` blocked | Connector/fake asks for real gateway/provider/model/network/credential/writer/registration/ACP/subagent/channel | Fake path returns fixed refusal before external effect; no statement about real runtime qualification | Injected-port/spawn/network/FD traces show zero forbidden action; D rows remain explicitly untested |
| ConvMem guarantee weakened | 13, 18, 21–27, 41–44, 49–52, 57–58 / B/C | `STATIC`/`FAKE`, fixture-only | Remove scope ceiling, terminal precedence, approval separation, provenance binding, protected helper, private/public boundary, or manager emptiness check | Independent negative control fails; unmodified implementation remains green | Each enforcement-removal mutant is red against a reference-owned expected result |
| Reviewed-plan substitution | Architecture §§18.8, 18.22 / M11 only | `STATIC`, pre-import control plane | Omit one of the five current reviewed paths; change one blob or mode; classify a sixth plan path; use an unavailable overlay commit or non-regular entry | Fail before runtime verification, source export, integration import or tests; no fallback and no widening of the product allowlist | Packet negatives plus independent `git ls-tree`/blob-ID proof; exact five reviewed documents still appear in exported source inventory and source-tree hash |
| Pylint gate bypass | Architecture §18.9 / M11 only | `STATIC`, merge-readiness control | Raise/regenerate the baseline; edit workflow/gate/config; exclude a path; use `--exit-zero`, `skip-file`, broad suppression or a 45th edit path | Fail the held checkpoint before acceptance evidence; actual unchanged current-main gate must still run and pass | Exact protected blob IDs, 44-path diff proof, suppression inventory, raw full-tree report and zero-exit regression-gate output |
| Pytest differential laundering | Architecture §18.10 / M11 only | `STATIC`, merge-readiness control | Use different path bytes; retain state between slot resets; omit a node/mismatch; rewrite arbitrary hashes; add a sixth R2b node; change the 118-member manifest or a second governed member; run one tip only; relabel retained failure as PASS | `PAUSE`; candidate earns no differential verdict and no merge-readiness claim | Exact source trees/environment/reset hashes, equal complete node sets, raw/JUnit/canonical records, symmetric reruns, exact five-node structured records, both authority manifests/Git-byte/digest proofs and retained-failure ledger with `FULL_PYTEST_PASS=false` |
| M8 authority-packet drift | Architecture §18.11 / M11 only | `STATIC`, pre-import and final-evidence control | Leave either old parent/overlay literal; alter a third path or nonliteral byte; make the declaration and frozen assertion disagree; run with a plan SHA other than the reviewed semantic parent | Runner and packet checks fail before fixture/runtime effect; no evidence transfers across the changed source; any extra edit is `PAUSE` | Exact two-path/four-substitution diff, declaration/assertion equality, four reviewed blob IDs, unchanged non-plan bytes, fresh final-source differential/Pylint and two exact M8 PASSes |
| Bundle-schema literal drift | Architecture §18.12 / M11 only | `STATIC`, production-boundary regression control | Retain `convmem.strict-fixture-work.bundle.v2`; alter a schema or test expectation; change a second source byte/path; skip fresh evidence because the edit is one literal | The existing M8 strict suite remains the oracle: only the publisher literal becomes `convmem.strict-fixture-bundle.v2`; tests are unchanged; any extra edit or retained `bundle_schema` failure is `PAUSE` | Exact one-path/one-substitution diff, unchanged test/schema blobs, fresh final-source differential and Pylint PASS, two exact M8 PASSes, seven MCP passes and unchanged runtime inventory |
| Post-bundle authority-packet drift | Architecture §18.13 / M11 only | `STATIC`, pre-import and final-evidence control | Keep the preceding parent/overlay; change only declarations or only assertions; alter a fifth literal/third path; revert the corrected publisher; run with a plan SHA other than the newly reviewed semantic parent | Runner and packet checks fail before fixture/runtime effect; declarations and assertions must equal the grant-named parent/overlay; the publisher fix remains exact; any extra edit is `PAUSE` | Exact two-path/four-substitution diff, declaration/assertion equality, publisher-literal proof, four reviewed blob IDs, unchanged remaining non-plan bytes, fresh final-source differential/Pylint and two exact M8 PASSes |
| Current-main reconstruction drift | Architecture §18.14 / M11 only | `STATIC`, merge-readiness control | Rebase/merge the preserved branch; resolve the STATUS conflict; omit/add a product path; copy a fifth control-plane path; make a seventh identity substitution; transfer the historical evidence verdict; let `origin/main` move | `PAUSE` before evidence, PR or merge. The new branch must equal exact current main plus the closed 120-path product set, four reviewed blobs and six identity substitutions | Independent `M/D/C/P` counts and hashes, three held commit diffs, Git blob/mode proof, 119-member R2b proof and final upstream-ref check; completed reconstruction preserved at `30bc134d` |
| Three-tip differential laundering | Architecture §18.15 / M11 only | `STATIC`, merge-readiness control | Require current main to govern nodes it never contained; omit `R`; reuse its different-slot historical signatures; exclude one of the 238 nodes; change a frozen node/outcome digest; let `R` govern an `N` node; accept a new `F`-only failure; add normalization or a sixth R2b exception | `PAUSE`; no differential verdict and no later evidence. Fresh `N`/`R`/`F` runs share one reset slot. `N` governs its nodes; `R` governs only `S = F - N`; retained failures stay debt and keep `FULL_PYTEST_PASS=false` | Exact three source tips, environment/reset hashes, three complete raw/JUnit/canonical sets, 238-node identity/outcome digests, symmetric `R`/`F` reruns, exact five-node R2b proof and positive token only `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` |
| Advanced-current-main drift | Architecture §18.16 / M11 only | `STATIC`, merge-readiness control | Continue after `origin/main` moves; branch from `d276cb4`; replay/cherry-pick old commits; alter the 11-path advance; omit/add a product path; use stale R2b identities; make a seventh substitution; transfer the unexecuted grant | `PAUSE` before reconstruction or evidence. The new branch starts at exact `5c6a4a8` and reaches exactly three held commits; preserved branches remain immutable | Independent `A/Q/M/D/P/C` hashes and intersections, three held diffs, four overlay blob proofs, exact six substitutions, 120-member R2b proof, absent prior slot/run root and final upstream-ref check |
| Inner-role signature laundering | Architecture §18.17 / M11 only | `STATIC`, merge-readiness control | Project a 23rd node; accept a different outcome/type/core/line count/tail; normalize the full environment, ordering, temporary suffix, hash or arbitrary text; omit one of the four `R`/`F` complete/rerun records; delete or rewrite raw evidence; infer PASS from the projection alone | `PAUSE`; only the exact 22-node set/hash and four-line grammar may map to the closed signature. Raw failure/JUnit bytes remain retained, every other differential gate still applies, and `FULL_PYTEST_PASS=false` | Exact node inventory/hash, independent four-line parser negatives, four-record proof per node, raw-to-projection hash mapping, unchanged §18.10 allowlist, closed five-node R2b proof and positive token only after the full fresh three-tip comparison |
| Reconstruction Pylint laundering | Architecture §18.18 / M11 only | `STATIC`, merge-readiness control | Call the three pairs inherited; suppress `R0801`; edit a baseline/gate/workflow/config/flag; exclude paths; change a reference/production module; use a helper/shared oracle; combine identity and lint edits; accept a targeted or non-current-main report | `PAUSE`; only the exact three construction-style rewrites in two named test files are eligible. The actual unchanged full-tree gate must report exactly 455 findings/69 `R0801`, no closed pair or new pair, and exit zero after a fresh differential | Sealed current-main/candidate reports and triage hashes, exact introduced-pair file, three held commit diffs, suppression/import/helper inventories, protected-blob equality, raw full-tree report and zero-exit gate output |
| Pylint acceptance-drift laundering | Architecture §18.19 / M11 only | `STATIC`, merge-readiness control | Treat protected-gate zero as exact acceptance; reuse the disposable probe; retain either added pair; accept 455 or any merely lower count; edit a second correction path; change the Gate-C tuple/reference/production byte; alter argument/key order; add helper/import/suppression | `PAUSE`; only the exact argument reorder and two-stage ordered dictionary in `tests/test_strict_evidence_state.py` are eligible. After fresh differential, unchanged full-tree Pylint must report exactly 454/69/240, no fatal/usage bit, empty stderr, gate zero and complete normalized pair-multiset equality to `N1` | Sealed `c71d37a` PAUSE packet/hashes, three held commit diffs, exact one-path/two-transformation proof, protected-blob equality, raw full-tree report, normalized pair records and zero-exit gate output |
| Pylint `R0401` determinism laundering | Architecture §18.20 / M11 only | `STATIC`, merge-readiness control | Relabel the diagnostic probes as acceptance; run only final source; omit/falsify the seed; add another environment delta; accept raw-byte mismatch as semantic drift; sort/rewrite raw evidence; accept a lower/different count or hash; change source/CI/baseline/runtime | `PAUSE`; after a fresh three-tip PASS, run complete Pylint at `N1` and final source with sole addition `PYTHONHASHSEED=0`. Both must produce exact 458/29/69/240 and 429 non-`R0401`, gate zero and the three frozen semantic hashes while retaining raw reports | Sealed `caec5c6` PAUSE packet/hashes, four-run diagnostic manifests, exact environment/argv/inventory records, paired raw reports, canonical `R0401`/message-count/`R0801` identities and unchanged protected-gate output |
| M8 legacy-count laundering | Architecture §18.21 / M11 only | `STATIC`, final-evidence control | Exclude either added safety node; change selectors, four deselections, a test function, parser or failure rule; edit a third integer or second path; infer a new expectation from whatever a future run collects; reuse the PAUSED run as PASS | `PAUSE`; only collected `116→118` and passed `115→117` in `EXPECTED_LEGACY_JUNIT_COUNTS` are eligible. Each fresh legacy array must equal the historical accepted array plus exactly the two named current-main nodes, both passed, with no removed node or changed outcome | Sealed `9da6dd98` PAUSE ledger/manifest/diagnostic hashes, exact one-path/two-integer diff, unchanged selector/deselection/test blobs, two independently fresh identical 118/117 M8 arrays, seven MCP passes and unchanged runtime inventory |
| Doctor import refusal escapes health check | Architecture §18.22.1 / M11 | `STATIC`, process-level safety control | Fresh doctor process with `openclaw-strict`, fixed unknown sentinel, or injected sensitive `SystemExit` payload | `mcp_import` is a failed sanitized check; later doctor checks still run; normal doctor exits nonzero; raw profile/payload/environment never appears | Fresh-process stdout/stderr/status plus later-check sentinel; recognized shell/unset/full controls remain green |
| Fenced operation-ID replay | Architecture §18.22.2 / M11 | `STATIC`, crash/recovery safety control | Crash after fence before input; retry same ID/same or different bytes; durable-input ambiguity; malformed/symlinked/conflicting evidence | Ordinary publish refuses write-free while fenced. Pre-input recovery may restore predecessor only with no durable intent and consumes the ID. Durable intent remains fenced/recovery-required. Exact retry requires independently proved admitted input | Fault-point pre/post trees, operation/digest records, retained fence history, write-set proof, negative control preventing predecessor rebuild after durable intent |
| CI partition laundering | Architecture §18.22.3 / M11 | `STATIC`, required-check control | Omit/duplicate a node; select by failure; inject host inner-role env; change selector/deselection; fake PASS/JUnit; skip dependency; mutate runtime/containment flag | Required context fails. Exact `O∩Q=∅`, `O∪Q=U`, real process/JUnit/node evidence and every dependency success are mandatory | Exact GitHub merge-tree identity, complete sorted node hashes/outcomes, mutation-test matrix, qualified runtime inventory and CI-regression receipt |
| Mutable, unlicensed, incomplete or substituted qualified runtime | Architecture §§18.22.4, 18.23–18.24 / external gate | `STATIC`, delivery/provenance control | Reuse the rejected archive; omit one delivery-set role, nested component, file owner, source, recipe, license or notice; use a mutable release/`latest`, wrong manifest/archive/tree hash, symlink/special/path escape, rolling-host/cache repair/fallback, incompatible kernel/bwrap, or treat test/Kiro PASS as publication clearance | Fail before build, publication or qualified test import; unresolved provenance or `LICENSING_DISPOSITION=PAUSE` remains blocking; never partially publish, download a substitute, repair bytes or fall back to host | Exact component lock and file-ownership equality; binary/source/recipe/license/notice/source-delivery ledgers; three-role manifest/archive/extraction/tree hashes; immutable coordinate proof; pinned bwrap; closed negative controls; Kiro plus independent actual-byte provenance/licensing PASS |
| Provenance-lock packet laundering | Architecture §18.25 / external gate | `STATIC`, schema and future evidence control | Self-hash the manifest; place reviewer output in the sealed packet; add/omit a 14th/13th role; use noncanonical JSON, duplicate/unknown keys, dangling/multiple owners, incomplete nested closure, open unresolved row with PASS, ambient cache/search/current-host inference, ungranted redirect/origin, execute downloaded bytes, mutate/repair a final leaf or relabel a structurally valid PAUSE packet as build-eligible | Static review or future negative control rejects before build. Packet and review leaves remain separate/atomic/immutable; every reference and runtime-file ownership closes; build eligibility requires canonical empty unresolved ledger and three exact PASS verdicts | Exact schema/version/base/runtime/root bindings; 13-role inventory; independent ID/hash recomputation; packet/object/file equality joins; authority observation transcript; §18.25.5 mutants; disposition bound to manifest and every packet file hash |
| SBOM absent-version projection laundering | Architecture §18.27 / external gate | `STATIC`, schema-v3 identity control | Reuse/delete v1 or v2 staging; treat null and absence as equivalent; change the raw object, component path/hash/key set/name/identity; project another absent component; use a tag, branch, uppercase/non-40-hex revision, qualifier, subpath, percent alias, normalization, lookup or second route; omit the raw binding | `PAUSE` before any durable packet. Only the exact hash-bound `base64` object at `components/0` with the exact absent `version` member may project; explicit null and every other missing version reject; all other §18.25 rules remain unchanged | Exact v1/v2 stop identities and cumulative read counters, absent fresh v3 roots, raw SBOM/object/component/key-set proofs, exact `raw_version_state="absent"` projection, complete §18.27 positive/negative matrix and proof no v1/v2 object entered v3 |
| Schema-v3 P0 result laundering | Architecture §18.28 / external gate | `STATIC`, immutable-packet review control | Relabel structural completion as provenance closure; omit an unresolved row; reset the exhausted read ledger; rerun the collector; mutate/replace the packet; create the review disposition inside the packet; let the collector review itself; infer origin/license/source from installed metadata; acquire from an unreviewed origin | `PAUSE`; only the exact result/manifest/packet identities are reviewable. All 98,608 open rows remain blocking; the review root stayed separate and absent until its distinct grant, and no acquisition/build/publication follows from either Kiro PASS or the later disposition | Exact collector/result/manifest/packet hashes, staging/durable byte-mode equality, 651 object hashes, nine unresolved-group counts, five-pass/11,643,965,233-byte ledger, historical absent review root and later disposition bound to every reviewed hash |
| Pre-acquisition or host-path laundering | Architecture §18.29 / external gate | `STATIC`, planning and clean-build control | Omit/duplicate/reassign a component, file, edge or unresolved ID; guess an owner; treat package/PURL/metadata/SBOM/search/registry/cache/host hints as authority; multiply ceilings by batch; mutate the disposition; copy or rewrite a rejected ELF; use `patchelf`/`chrpath`, prefix replacement, host fallback, traversing `$ORIGIN`, inherited loader/Tcl/terminfo state, synthetic external libraries/data or a blanket absolute-path/debug exception | `PAUSE`; coverage must be disjoint and equal to the four manifest sets, unsupported origins stay unresolved, every operation is separately reviewed/granted, and the three path-bearing components are rebuilt only from independently locked inputs. Runtime PASS cannot override provenance/privacy/compliance failure | Exact disposition and manifest primary-key hashes; twenty-batch/49-page/19-file queue proof; packet citations; three object/path/offset/RPATH bindings; exact operation packet; two distinct-prefix build comparison; complete delivery-set host/build-prefix and loader-semantic scans |
| R2b content-attestation drift | Architecture §18.22.5 / M11 | `STATIC`, cross-arc merge control | 121st/missing member; changed seed/closure/route; third changed governed member; self-derived identity only; live gate/capture attempt | `PAUSE`; only inventory JSON may rotate after final edits; exact 120-member manifest and independent resolver/inventory/artifact identity must converge; no live effect | Before/after manifests, exact two-member change proof, independent identity recomputation, resolver/digest/artifact equality and existing R2b negative tests |

## 6. Live-supervision protocol

**Current controlling state:** `PAUSE`. PR `#342` is merge-blocked. No plan
application, corrective edit, runtime publication, evidence execution or PR update
may begin from this document. The first archive is rejected for publication; exact-tip
Kiro review of the pre-acquisition and clean-replacement plan is next. The replacement,
schema-v1/v2/v3 and result-binding reviews already PASSed at `3402e62a`, `5f397852`,
`2956f701`, `d03aa553` and `3b3550c`; the v1/v2 stops, v3 immutable PAUSE packet and
independent technical-PASS/provenance-and-licensing-PAUSE disposition authorize
nothing further. No PASS can authorize a collector rerun, runtime/evidence read,
origin resolution, acquisition, binary repair, component-lock derivation, download,
build, publication or external action. Those stages require separate reviewed packets
and Ryan grants. Only after all applicable
prerequisites and a later implementation grant may Cursor push, report and stop after:
(1) five-document plan application, (2) authority/
scope rebind, (3) doctor correction, (4) publisher/recovery correction, (5) CI
correction, and (6) independent R2b inventory rotation. Codex issues a new
commit-specific status after complete inspection of each hold. Runtime delivery is a
separate reviewed and Ryan-authorized external action, never an implicit checkpoint.

**Codex is the mandatory live supervisor.** The M0–M8, reconstruction,
reviewed-plan correction, 44-path remediation and differential identity holds
are complete on the preserved evidence branch. Its clean merge-ready tip is
`PRESERVED_M11_MERGE_READY_SHA`, but its evidence is bound to the historical
integration baseline. Exact-current-main reconstruction is separately preserved
at `PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA`; the stopped three-tip input is
preserved at `PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`; and the completed
advanced-main candidate plus governed signature PAUSE are preserved at
`PRESERVED_M11_INNER_ROLE_PAUSE_SHA`; the reviewed signature correction and
differential-PASS/Pylint-PAUSE source are preserved at
`PRESERVED_M11_PYLINT_PAUSE_SHA`; the first Pylint correction and governed
acceptance PAUSE are preserved at `PRESERVED_M11_PYLINT_ACCEPTANCE_PAUSE_SHA`;
and the §18.19 successor correction, fresh differential PASS and governed
determinism PAUSE are preserved at `PRESERVED_M11_R0401_PAUSE_SHA`. The reviewed
§18.20 plan/rebind, fresh differential and paired Pylint PASS, followed by the
final-M8 legacy-count PAUSE, are preserved at
`PRESERVED_M11_M8_COUNT_PAUSE_SHA`. Under a new grant, Grok must push/report and
stop after exact reviewed-plan application, after the two-file/four-substitution
identity commit, and after the one-file/two-integer count commit. Evidence starts
only after Codex proves all three held boundaries and issues a written `CONTINUE`
citing the exact final pushed commit. The supervisor
may issue only:

- `CONTINUE` — exact plan conformance and required evidence are present.
- `CORRECT` — an implementation defect can be fixed within the frozen contract.
- `PAUSE` — authority, scope, contract, persistence, permission, or irreversible
  boundary is unclear or changed; no further work until resolved.
- `REQUIRE TEST` — a required specified test/evidence item is missing.

The historical legacy-count PAUSE is closed by the evidence at
`PRESERVED_PR342_HEAD_SHA`; it is not the current stop. Ryan's present direction
authorizes only this four-document pre-acquisition and clean-replacement plan. Exact-
tip Kiro PASS is required before complete cited origin planning may be proposed. A
separate exact operation packet, review and Ryan grant are required before any
metadata resolution, provenance acquisition or retained-source read. Separate reviewed
plans and Ryan grants remain required for zero-unresolved lock closure, clean build,
final packet, external publication, CI admission and corrective implementation. All
preserved source branches and PR `#342` stay
unchanged until then. No
earlier `CONTINUE`, M8 grant, M11 grant or evidence verdict can be reused.

Before every `CONTINUE`, Codex inspects current diff, complete changed-file
list, commit and push state, raw runner output including declared future-T
reds, new dependencies, schema/data changes, permission/config changes, plan
deviations, and every claim lacking evidence. `CONTINUE` names the exact commit
and next permitted checkpoint; it cannot be reused after another commit.

`CORRECT` and `REQUIRE TEST` send work back to the same checkpoint. Grok makes
only the requested in-contract correction/test, commits and pushes, stops, and
receives a complete re-inspection; the prior status never authorizes progress.
`PAUSE` stops all implementation. Codex may clear a same-contract factual
misunderstanding in writing after re-inspection. A semantic/contract ambiguity
requires Kiro resolution; any changed semantic-parent or overlay SHA, scope, or
grant condition additionally requires a new Ryan grant before Codex may issue
`CONTINUE`.

Cursor must predeclare and report every command outside the reviewed test entrypoints.
It may inspect the worktree, apply the exact grant-named plan range, edit only the
current M11 held files, commit, push and run only grant-named targeted developer
tests. It may not merge/rebase/resolve conflicts, edit/squash reviewed plan commits,
publish the runtime, execute acceptance suites, alter evidence, or touch any unlisted
byte. Codex owns blob/tree/diff comparisons, runtime/delivery verification, complete
ordinary/qualified CI, publisher crash evidence, independent R2b convergence,
unchanged Pylint, two M8 executions, seven MCP regressions, GitHub check verification
and durable evidence collection.
Codex issues `PAUSE` before Grok proceeds on architectural drift,
invented/changed contract, trust-boundary change, persistent mutation,
migration, new permission, autonomous behavior, weakened guarantee,
irreversible action, or contradiction. It issues `REQUIRE TEST` for a missing
test, negative control, independent oracle, reproduction, or command record.
Routine conforming work inside a held-and-cleared checkpoint needs no Ryan
reapproval.

## 7. Ryan-confirmation gates

Ryan's explicit confirmation naming exact revisions is required before:

- initial T0–T5 implementation;
- the current M11 correction: exact `SEMANTIC_PARENT_SHA`, final
  `REVIEWED_OVERLAY_SHA`, `PR342_PLAN_BASE_OVERLAY_SHA`, PR base/head/tree,
  implementation branch, five reviewed control documents, exact authority/scope,
  doctor, publisher/recovery, CI and R2b inventory file sets, checkpoint order,
  runtime/evidence roots and the complete doctor/crash/CI/R2b/Pylint/M8/MCP
  evidence sequence;
- preparing or accepting complete cited origin work items beyond this contract, or
  creating an operation packet; the packet must preserve the exact baseline sets and
  name every HTTPS/VCS origin or retained-local root, method, redirect, request/retry/
  time/content/expanded ceiling, parser/tool identity, fresh coordinate, checkpoint,
  credential prohibition and failure disposition;
- making any metadata-resolution, provenance-acquisition, VCS or retained-source
  request, or deriving the replacement component lock, ownership map, artifact/source/build
  ledger, license/notice ledger or corresponding-source delivery matrix, or accepting
  a successor provenance packet;
- building the replacement runtime, compliance/corresponding-source archive or
  `delivery-set.json`, including every exact input, output root and toolchain;
- authoring or accepting the final packet that pins the three-role set;
- creating or publishing the exact GitHub Release tag and all three replacement
  assets, including repository/tag/names/sizes/hashes, extracted tree hashes,
  provenance/licensing, extraction rules, hosted-runner compatibility and replacement
  policy; no such grant is eligible while `REPLACEMENT_PROVENANCE_CLOSURE` is not
  closed, `REPLACEMENT_PUBLICATION_ELIGIBLE=false` or
  `REPLACEMENT_LICENSING_DISPOSITION=PAUSE`;
- admitting the complete replacement set into hosted CI after publication;
- supplying/provisioning the exact test runtime or making any host write for it;
- changing or contradicting Ryan's ratified refusal-contract ruling;
- any ConvMem core data-model change **beyond the exact parent-specified and
  granted T0–T5 fixture contract**;
- any trust, signing, approval, provenance, eligibility, or unitization change
  beyond that exact fixture contract;
- persistent storage or migration beyond the parent-defined disposable fixture,
  and any live admission or live data access;
- any new OpenClaw permission, tool, process, service, user, socket, mount,
  network, credential, provider, model, plugin installation, or config change;
- autonomous memory writes, capture, indexing, redistillation, or tool action;
- rollback/recovery semantic change or weakening/removal of an invariant;
- Gate D, Gate W, Gate D-V, Gate E, Gate F, watch coverage, or promotion;
- expansion beyond the approved web-development use case;
- adoption of any code baseline other than the exact reviewed
  `CURRENT_MAIN_BASELINE_SHA`, creating a PR, merge, deployment, irreversible
  repository action, or external consequence.

## 8. Separate risk verdicts

- **ConvMem alone — AMBER, bounded implementation accepted:** the parent
  preserves legacy semantics; historical M8 was accepted, and all bounded M11
  evidence plus Kiro conformance PASS at `PRESERVED_M11_MERGE_READY_SHA`.
  The reviewed inner-role correction and differential PASS are preserved at
  `PRESERVED_M11_PYLINT_PAUSE_SHA`; the first Pylint correction and fresh
  differential are preserved at `PRESERVED_M11_PYLINT_ACCEPTANCE_PAUSE_SHA`;
  the exact §18.19 correction and fresh differential are preserved at
  `PRESERVED_M11_R0401_PAUSE_SHA`; and the §18.20 plan/rebind plus passing fresh
  differential and paired Pylint are preserved at
  `PRESERVED_M11_M8_COUNT_PAUSE_SHA`. The later 118/117 correction and complete
  three-tip/Pylint/M8/MCP evidence passed at `PRESERVED_PR342_HEAD_SHA`; current
  merge readiness is blocked by PR required pytest, two safety defects and the absent
  publishable qualified-runtime set. Gate W and live data remain BLOCKED.
- **OpenClaw alone — RED for real/runtime use; AMBER for connector/protocol
  fake:** the fake is deliberately non-authoritative and uninstalled, and no
  OpenClaw process runs in T0–T5. Real authentication, containment,
  distribution, credentials, manager proof, and tool permissions are
  unresolved, so no real OpenClaw verdict or use is authorized.
- **Integration — AMBER for the preserved bounded fixture; RED/BLOCKED for PR
  merge and pilot/production:** PR `#342` has a red required pytest context and
  two confirmed safety defects. The replacement delivery-set plan has Kiro PASS; its
  schema-v1 and schema-v2 P0 attempts are stopped, while schema-v3 P0 produced an
  immutable but unresolved PAUSE packet. Result binding and independent disposition
  are complete; technical PASS remains provenance/licensing PAUSE. This
  pre-acquisition/clean-replacement plan awaits exact-tip Kiro review, followed by
  complete cited origin planning, separately reviewed/granted operations, acquisition,
  zero-unresolved lock, clean build, packet, publication and
  CI-admission stages. The combined system is not operationally complete until
  Gate D/W, Gate D-V/E, live evidence, maintenance/watch and promotion pass.

## 9. Unresolved decisions that must be resolved before Grok resumes

No earlier T0–T5 or completed M11 architectural decision is reopened. The schema-v3
collector, P0 and disposition are complete and cannot run again. Kiro must PASS this
exact pre-acquisition/clean-replacement parent and overlay. Complete cited origin work
items and any access require a new exact operation packet, review and Ryan grant naming
origins, methods, redirects, tools, ceilings, roots and checkpoints. Kiro
and the independent licensing reviewer must PASS a later zero-unresolved lock before a
separately granted build; and a new exact final
packet plus actual-byte reviews must PASS before publication is eligible. Before
Cursor resumes the PR correction, Ryan must name
the PR/base/head/tree, implementation branch, five reviewed control documents,
exact held file sets/order, runtime/evidence roots and full evidence authority.
Runtime publication additionally requires the complete replacement set and an exact
external-action grant; the rejected archive is never eligible. Codex must freshly
verify refs, plan blobs, source
tree, runtime inventory/distribution, evidence roots and clean worktrees before
the first written `CONTINUE`. A missing prerequisite blocks work.

If “Grok starts” means any real runtime, writer, pilot, live use, or promotion,
the following remain unresolved and block work: exact authentication route;
sealed runtime/distribution and containment adapters; Gate W production
admission/writer paths and migration posture; permissions and external config;
watch-coverage final verdict/activation; pilot tasks, methodology, leakage
controls, metrics, rollback, and allowed actions; promotion criteria.

## 10. Grok must not decide

For this successor correction, Cursor/Grok must not decide how doctor refusal is
contained, when a fence may clear, whether an operation ID can be reused, how CI
partitions nodes, which runtime artifact is trusted, which documents/files are
allowed, which R2b members changed, or which evidence grants PASS. Those choices
are frozen by §18.22/§10.20 and the later Ryan grants. Cursor may not publish the
runtime or run acceptance evidence; §18.23/§10.21 also forbid Cursor/Grok from
choosing archive tools/bytes, extraction, bwrap, provenance/licensing disposition,
coordinates or replacement policy. Sections 18.24/10.22 additionally forbid Cursor/
Grok from choosing component/file ownership, artifact/source identity, transformation,
build recipe/toolchain, license selection, notice/source obligation, delivery-set
role, manifest schema, final coordinate or whether an unresolved row is acceptable.
Sections 18.25/10.23 additionally forbid them from choosing a provenance field/type/
enum/null case, file role, primary key, ID/hash encoding, packet/object join, root,
source authority, redirect, acquisition method, unresolved disposition or negative
control. Sections 18.26/10.24 additionally preserve the failed explicit-null design.
Sections 18.27/10.25 forbid reuse or deletion of v1/v2 staging and any component-
version derivation beyond the exact object/component/key-set/path-bound absent-member
projection. Kiro schema-v3 PASS cannot be treated as collector-freeze or P0 execution authority.
Codex owns evidence, and an independent lane
owns final R2b manifest derivation.

Grok must not decide or change schemas, fields, enums, hashes,
canonicalization, identity, trust, signer/issuer, approval, provenance,
eligibility, unitization, state reduction, publication order, rollback,
recovery, interfaces, tools, aliases, parent-frozen error contracts, limits,
permissions, dependencies, mounts, peers, runtime/auth/provider/model, storage,
migrations, capture,
indexing, pilot methodology, evaluation thresholds, gate ownership, allowed
files, branch base/creation, checkpoint order, supervisor holds, evidence
location, integration method, conflict resolution, commit selection/order,
current-main byte handling, or promotion. In M11 Grok may not choose the
control-plane paths, blob/mode rule, node-authority partition, source-hash
membership, commit order, correction path set, fixture or presentation
behavior. The grant-named 120 product paths, four control blobs and six identity
substitutions were completed and preserved at
`PRESERVED_M11_PYLINT_PAUSE_SHA`; the first Pylint correction is preserved at
`PRESERVED_M11_PYLINT_ACCEPTANCE_PAUSE_SHA`; and the §18.19 correction plus
fresh differential/Pylint PAUSE is preserved at `PRESERVED_M11_R0401_PAUSE_SHA`.
The §18.20 plan/rebind plus fresh differential/paired-Pylint PASS and final-M8
count PAUSE are preserved at `PRESERVED_M11_M8_COUNT_PAUSE_SHA`.
The historical legacy-count sequence is complete at `PRESERVED_PR342_HEAD_SHA`.
The only possible next implementation, after Kiro and new grants, is the exact
held five-document plan/scope, doctor, publisher/recovery, CI and independent
R2b inventory sequence in current M11, followed by Codex-owned evidence.
The earlier reconstructions, publisher, authority-packet and 44-path corrections
are already preserved. Grok may not choose `N1`, `R`, `F`, the parent or overlay
value, edit test logic, add a fifth plan path, third identity file or fifth
literal, third integer, second count-correction path, change selectors or the
four deselections, change `CODE_BASELINE_SHA`, change formatting/logic, resolve a conflict,
edit/squash/reorder the reviewed plan range, or infer authority from
the historical PASS.
It must not raise/regenerate or fork the Pylint baseline, edit
workflow/gate/config/flags, exclude files, choose a 45th path, waive a finding,
add any suppression for the §18.19 correction, add a helper/import, change the
§18.18 Gate-C tuple or any reference/production module, couple an independent oracle to production, or
substitute a preserved-tip/targeted comparison for the actual current-main
Pylint gate. It must not choose the Pylint seed, environment delta, semantic
record fields, canonical encoding, counts/hashes, or make raw ordering an
oracle. It must not choose the three pytest tips, which tip governs a
node, environment, reset paths, normalizations, identity parser/oracle,
mismatch disposition, rerun set, retained-failure classification or verdict token. It
must not choose the 22-node set, semantic-signature line grammar, raw-to-projection
mapping, or apply that projection to any other record. It
must not choose report paths,
JUnit family, node reconstruction, outcome vocabulary, canonical evidence
fields, expected counts, failure rules, runtime/evidence paths, or which tests
run. The parent and later Ryan grant freeze all of them.

## 11. Final build-readiness gate

**Bounded T0–T5 verdict: IMPLEMENTED, TESTED AND ACCEPTED AT THE HISTORICAL
TIP. BOUNDED M11 EVIDENCE: PRESERVED AT `PRESERVED_PR342_HEAD_SHA`. PR MERGE
READINESS: FAIL / BLOCKED. REPLACEMENT-DELIVERY PLAN: KIRO PASS.
PROVENANCE-LOCK SCHEMAS V1/V2: P0 PAUSE. SCHEMA V3: IMMUTABLE P0 PAUSE PACKET;
RESULT BINDING AND INDEPENDENT DISPOSITION COMPLETE; PRE-ACQUISITION/CLEAN-
REPLACEMENT PLAN READY FOR KIRO EXACT-TIP REVIEW;
CURSOR REMAINS PAUSED.** The first runtime packet already passed Kiro but failed
independent publication provenance/licensing review. The replacement delivery-set
plan passed at `3402e62a`; schema v1 passed at `5f397852`, then its offline P0 stopped
on a component initially classified as null-version. Schema v2 passed at `2956f701`,
then its one P0 proved the raw `version` member is absent and stopped without a result
or durable packet. Schema v3 passed at `d03aa553`, then its one P0 published immutable
packet tree `491ae60b…` and honestly retained 98,608 open rows. This overlay freezes
the exact disposition, lossless coverage and host-path clean-replacement boundary. No
collector rerun, runtime/evidence read, origin resolution, acquisition, binary repair,
lock closure, build, final packet, publication or
CI-admission stage is authorized. Required GitHub pytest is red, doctor and
publisher safety corrections are unimplemented, GitHub runtime distribution is
unpublished and currently ineligible because provenance/licensing remains `PAUSE`,
and R2b authority-content identity is not converged for the final corrective tree.
After Kiro pre-acquisition-plan PASS, every later §§18.24–18.29/§§10.22–10.27 stage and the M11
implementation still require separate exact Ryan grants and reviews. This overlay authorizes no
product/test/CI/inventory/runtime edit, evidence execution, PR update or merge.

**Complete ConvMem–OpenClaw system verdict: NOT BUILD-READY.** Gate D real
runtime, Gate W governed writes, Gate D-V evaluation, Gate E limited web pilot,
watch coverage, and promotion are intentionally unresolved and separately
Ryan-gated. Their absence is not delegated to Grok and must not be hidden by a
successful fixture build.

## TL;DR

- The exact `1b71fcc9958716323fa0b7a2467218f4e9fde5b0` semantic parent is the
  current source of truth; this overlay only sequences, supervises and gates it.
- M0–M8 and the complete historical M11 evidence passed; the preserved source
  is `cd60cf19`; exact-current-main reconstruction is preserved at `30bc134d`.
  Its three-tip correction reached `d276cb4`; the advanced-main reconstruction
  reached `776a4ca3`; the reviewed inner-role correction and fresh differential
  then passed at `65bbfd6f`; the first Pylint correction reached `c71d37a` and
  paused at 456/71. The exact §18.19 successor correction and fresh differential
  passed at `caec5c6`; the §18.20 plan/rebind then reached `9da6dd98`, where the
  fresh differential and paired seeded Pylint passed. Final M8 run 1 paused only
  because two added passing current-main safety nodes made the legacy result
  118/117 against the historical 116/115 expectation.
- PR `#342` exists at `94f29eb` but is merge-blocked by required pytest and two
  safety defects. M11 now freezes held doctor, publisher/recovery, complete
  ordinary/qualified CI, immutable runtime delivery and R2b convergence work. The
  557,628,743-byte local archive passes exact byte/mode/extraction validation and Kiro
  packet review but fails independent publication provenance/licensing review. It is
  immutable and rejected. The three-role replacement plan passed Kiro at `3402e62a`.
  Schema v1 froze a canonical thirteen-role provenance packet and passed Kiro at
  `5f397852`, but offline P0 stopped on a component initially classified as null-version.
  Schema v2 passed Kiro at `2956f701`; its one run proved the raw member is absent and
  stopped before result or durable packet creation. Schema v3 passed Kiro at
  `d03aa553`; its one granted P0 produced immutable packet tree `491ae60b…` at the
  exact read ceiling and honestly retained 98,608 open rows. Kiro passed the
  §§18.28/10.26 result binding at `3b3550c`; Claude then wrote disposition
  `45442e93…`, which Codex verified as technical `PASS`, provenance/licensing
  `PAUSE`, with all open IDs retained. Sections 18.29/10.27 now freeze lossless
  pre-acquisition coverage and clean replacement for the three host-path-bearing ELF
  objects; exact-tip Kiro review is next. Acquisition, zero-unresolved lock closure,
  build, final packet, publication and CI admission remain separately gated; merge is
  a later Ryan decision.
- Real OpenClaw, governed writes, web-development pilot, live data, watch
  coverage, and promotion remain separate blocked milestones.
