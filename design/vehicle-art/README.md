# Vehicle artwork explorations

The iOS app currently renders vehicle identity with SF Symbols. See
[`carodo-ios/docs/design-system.md`](../../../carodo-ios/docs/design-system.md#vehicle-artwork-and-paint)
for current behavior. These vector experiments are historical design references, not the shipped
renderer and not approval to replace it.

- [`archive/rounded-v4/`](archive/rounded-v4/README.md): earlier rounded vector set, 10 silhouettes.
- [`archive/detailed-v4/`](archive/detailed-v4/README.md): later detailed variant, 11 silhouettes,
  including the bicycle. Formerly stored under the ambiguous name `design/c/`.

Each archive keeps its generator, SVGs, HTML gallery, palette and PNG review sheets together.
Both variants called themselves v4; the descriptive names distinguish them without inventing a
new product version. Do not delete one as a duplicate: most geometry differs.

Export into a temporary file for inspection. Exporters are historical and may require adaptation
to current app types; never overwrite app code as part of organizing this archive.
