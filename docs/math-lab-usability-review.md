# Interactive laboratory review record

Read-only independent reviewer checked the increment against base4312d91. Three important findings were reproduced before fixes:

- Library insertion at the12compute-node limit edited the existing selected node. `createNode(kind,template)` now validates the entire proposed node/document before changing state; browser failed-add regression passes.
- Escape removed drag preview without removing pointer listeners. Gesture cancellation now removes document listeners; browser drag/Escape/reconnect regression passes.
- The new Math port was only used by v2, while health/legacy routes still used8788. All bridge calls now use validated fixed-loopback engine_url and implicit correct Host. Python regression covers health/evaluate/graph/ports/formula on a selected test port.

The reviewer also identified viewport span retention after the result domain shrinks. Added a real-Math history/viewport regression, observed RED, clamped the viewport span and observed GREEN. No deferred review findings remain in this scope.

Execution rulings: retain pinned backward-compatible Math321c4cd rather than adopting an uncommitted v2.1 contract. New Math v2.1 model/multi-port features require a separately pinned adapter and are not advertised here. Catalogue methods and references supported by the current pinned v2 are selectable. No numerical algorithm, units parser or book definition runs in Terminan.

User-reported physical chain and isolated Windows reproduction are distinct: original human physical receipt was not found; automated real-Math E2E validates literal[5,17,37] with synthetic/manual source data, test-owned free ports and false authority flags. Working ADMINIT installation is unchanged.
