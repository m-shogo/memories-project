# memories-project

AI記憶体サービスの構想・仕様・実装方針をまとめるリポジトリ。

このサービスは ChatGPT / Claude / Gemini / Character.AI の代替ではない。

目的は、AIと会話することではなく、AI時代に失われやすい「自分の人生の文脈」を持ち続けること。

## 一言で言うと

**AI時代、自分という文脈を持ち続けるための記憶体。**

AIは変わる。モデルも変わる。サービスも変わる。

でも、ユーザー自身の人生の文脈だけは、この記憶体が持ち続ける。

## 目指すもの

- 相談AIではない
- 雑談AIではない
- 人格AIではない
- Character.AI ではない
- 日記アプリだけでもない
- 写真管理アプリでもない
- パスワード管理ツールではない
- 会社の便利検索ツールではない

作るものは、人生の断片を集め、意味でつなぎ、必要な時に思い出せる **人生の文脈レイヤー**。

## コア思想

ユーザーが保存したいのは「AIとの会話」そのものではない。

本当に保存したいのは、そこに含まれる

- 悩み
- 趣味
- 人間関係
- 将来
- 価値観
- 思い出
- 判断基準
- 好み
- 変化

である。

## 重要な差別化

既存AIサービスは、サービスごとに記憶が閉じている。

ChatGPT、Claude、Gemini、X、Googleフォト、GitHub、Notion、カレンダーなど、人生の断片はあらゆる場所に分散している。

このサービスは、それらをすべて一箇所へコピーするのではなく、**どこに何があり、それが人生の中でどういう意味を持つか**を覚える。

## 最初に大事にすること

初回体験のハードルを低くする。

いきなり ZIP インポートや複雑な連携を要求しない。

まずは診断と最初の記憶から始める。

その後、ユーザーが価値を理解してから、ChatGPT エクスポート ZIP、X アーカイブ、Googleフォト、GitHub、Notion などの取り込みへ進める。

## Docs

- [Concept](docs/concept.md)
- [Product Principles](docs/product-principles.md)
- [Product Boundaries](docs/product-boundaries.md)
- [Memory Constitution v1](docs/memory-constitution-v1.md)
- [Personal Context Model](docs/personal-context-model.md)
- [Personal Memory Extraction Rules](docs/personal-memory-extraction-rules.md)
- [Sensitive Response Guardrails](docs/sensitive-response-guardrails.md)
- [Import / Export Strategy](docs/import-export-strategy.md)
- [Export Format Research](docs/export-format-research.md)
- [Niche AI Imports](docs/niche-ai-imports.md)
- [Import Security Checklist](docs/import-security-checklist.md)
- [MVP Roadmap](docs/mvp-roadmap.md)
- [Pricing and Cost Guardrails](docs/pricing-cost-guardrails.md)
- [Memory Data Model](docs/memory-data-model.md)
- [Fable Review Prompt](docs/fable-review-prompt.md)
- [Fable Review and DB Hardening Addendum](docs/fable-review-and-db-hardening-addendum.md)
- [Privacy and Ethics](docs/privacy-and-ethics.md)
