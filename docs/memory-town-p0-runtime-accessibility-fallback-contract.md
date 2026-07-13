# Memory Town P0 Runtime, Accessibility and Fallback Contract

最終更新: 2026-07-13

## 目的

PixiJS / WebGL導入時に、非同期初期化、route離脱、accessibility tree重複、context loss、asset failureでMemory Town全体が不安定になることを防ぐ。

この文書は次の範囲で既存文書より優先する。

- renderer initialization
- ticker lifecycle
- accessibility interaction tree
- fallback mode
- context loss / restore
- asset load lifecycle

実装はまだ開始しない。

---

# 1. PixiJS version and renderer selection

## 1.1 Version policy

- package manager lockfileでPixiJSのexact versionを固定する
- `^8.x`のようなfloating rangeだけでproduction buildしない
- version upgradeはdependency updateではなくrenderer compatibility changeとしてreviewする
- major / minor upgrade時はfixture、visual regression、context loss、accessibilityを再検証する

## 1.2 Renderer policy

Memory Town MVPはWebGLを明示する。

```ts
const app = new Application();

await app.init({
  preference: 'webgl',
  preferWebGLVersion: 2,
  sharedTicker: false,
  autoStart: false,
});
```

Rules:

- WebGPUへ自動移行しない
- WebGPU採用は別のADRとperformance / privacy / compatibility gateを必要とする
- WebGL2 unavailable時のWebGL1 fallback可否はprototypeで確認する
- renderer unsupported時はFunctional Fallbackへ移行する

---

# 2. Renderer lifecycle state machine

```ts
type TownRendererLifecycleState =
  | 'idle'
  | 'initializing'
  | 'ready_paused'
  | 'ready_running'
  | 'context_lost'
  | 'degraded'
  | 'disposing'
  | 'disposed';
```

許可transition:

```txt
idle → initializing
initializing → ready_paused
initializing → degraded
initializing → disposing
ready_paused → ready_running
ready_running → ready_paused
ready_running → context_lost
ready_paused → context_lost
context_lost → ready_paused
context_lost → degraded
ready_* → disposing
degraded → disposing
disposing → disposed
```

禁止:

- disposedからresume
- 同一sessionで二重init
- context lost中のscene mutation
- route離脱後のasync completion反映

---

# 3. Session generation and cancellation

Renderer mountごとに単調増加するgenerationを割り当てる。

```ts
interface TownRendererSession {
  generation: number;
  abortController: AbortController;
  lifecycleState: TownRendererLifecycleState;
}
```

全async taskは開始時generationをcapturedし、完了時に次を確認する。

```txt
captured generation == current generation
AND lifecycle not disposing / disposed
AND abort signal not aborted
```

対象:

- `Application.init()`後処理
- asset manifest load
- texture load
- scene composition
- context restore
- delayed camera animation
- telemetry flush

route leave時:

```txt
abort
→ ticker stop
→ event listener解除
→ DOM overlay無効化
→ renderer destroy
→ generation increment
```

stale completionはno-opとし、UI stateを書き換えない。

---

# 4. Ticker policy

PixiJS shared tickerを使用しない。

```txt
sharedTicker = false
autoStart = false
```

Start条件:

```txt
route active
AND document visible
AND renderer ready
AND minimum assets ready
AND SceneSnapshot accepted
AND motion policy requires continuous frames
```

Stop条件:

- route leave
- hidden tab
- context loss
- disposing
- motionLevel = offでstate変化がない
- low power policy

## 4.1 Render-on-demand

`motionLevel = off`では常時tickerを動かさない。

以下の時だけ1frame renderする。

- SceneSnapshot change
- viewport resize
- selection change
- focus change
- theme / contrast change
- context restore

`motionLevel = reduced`の具体fpsはprototypeで決める。

---

# 5. Application and Assets initialization order

順序を固定する。

```txt
create Application
→ await app.init
→ verify renderer/session
→ Assets.init with versioned manifest
→ load minimum fallback/core bundle
→ compose or accept SceneSnapshot
→ create visual scene
→ create authoritative DOM interaction tree
→ start ticker only if needed
```

Application init前にPixi textureを前提とするasset pipelineを開始しない。

---

# 6. Asset bundle lifecycle

Bundle候補:

```txt
town-core-fallback
main-island-base
main-island-structures
main-island-props
season-spring
season-summer
season-autumn
season-winter
district-<stable-id>
```

Rules:

- stable asset aliasはAsset Manifestの`textureKey`
- URLやatlas filenameをdomain IDにしない
- alias collisionはmanifest activation前に拒否
- core fallback bundleはroute中常駐
- seasonal / district bundleはlazy load可能
- unloadはobject referenceが0であることを確認してから行う
- unload failureでTown stateを消さない
- manifest version切替はatomic
- old manifestで描画中にaliasをin-place置換しない
- private memory URLをasset resolverへ渡さない

---

# 7. One authoritative accessibility tree

## 7.1 Production rule

Authoritative interaction treeはReact / DOMの一つだけとする。

```txt
TownSceneSnapshot
→ visual Pixi scene
→ semantic DOM interaction model
```

Canvas:

```html
<canvas aria-hidden="true"></canvas>
```

Building / feature interaction:

- DOM button
- stable feature ID
- accessible name
- current stage / current countのsafe description
- route action
- visible focus indicator

PixiJS accessibility plugin:

```txt
production: disabled
debug comparison: optional
```

理由:

Pixi accessibilityもDOM overlayを生成するため、独自DOM overlay / listと同時利用するとduplicate focus targetになり得る。

## 7.2 Overlay and list modes

同一semantic modelから二つのpresentationを作れる。

```txt
spatial overlay mode
object / feature list mode
```

ただし同時に両方をTab対象にしない。

- overlay mode active時、list modeはnavigation landmarkから明示切替
- list mode active時、overlay buttonsは`inert`または非focusable
- selected featureはmode切替後も維持

## 7.3 Tab order

Tab orderはscreen Yやz-indexでは決めない。

Feature Registryのstable navigation orderを使う。

初期候補:

```txt
central square
cinema
story house
market
port
warehouse
```

順番はuser comprehension test後に固定する。

## 7.4 Future editor

Keyboard / screen readerのeditor正本:

- DOM object list
- DOM placement form
- DOM move controls
- DOM undo / redo
- DOM validation issues

Canvas dragは補助入力であり唯一の編集方法にしない。

---

# 8. Fallback levels

## 8.1 Functional Fallback — mandatory

```txt
DOM feature buttons
+ feature / object list
+ summary sheet
+ normal navigation
```

常に利用可能。

WebGL failureでもMemory OS本体機能を失わない。

## 8.2 Layered Visual Fallback — MVP candidate

```txt
base map image
+ per-object DOM images
+ per-stage image selection
+ DOM buttons
```

MVP fixed layoutでは、logical positionをCSS positionへprojectionして表示可能。

これは一枚の完成画像ではない。

## 8.3 Cached Snapshot Fallback — optional

- previously generated town thumbnail
- last known visual preview
- exact current stateを保証しない
- timestamp / stale indicator必須
- interactionの正本にしない

## 8.4 Prohibited promise

```txt
single static image always equals current dynamic Town
```

は保証しない。

---

# 9. Context loss and recovery

Canvasへcontext loss listenerを登録する。

Loss:

```txt
prevent default restoration behavior where required
→ lifecycle = context_lost
→ ticker stop
→ visual canvasを操作不可にする
→ Functional Fallbackを表示
→ current SceneSnapshotを保持
→ no layout / progress mutation
```

Restore:

```txt
session generation確認
→ asset manifest再確認
→ GPU resource再構築
→ latest accepted SceneSnapshotからscene再構築
→ DOM semantic tree整合確認
→ ready_paused
→ policyに応じstart
```

一定回数以上restore失敗:

```txt
lifecycle = degraded
Functional Fallbackを継続
```

自動reload loopを作らない。

---

# 10. Resize and camera synchronization

DOM overlayとPixi sceneは同じprojection resultを使う。

```txt
logical geometry
→ camera transform
→ viewport / safe area transform
→ visual bounds
→ DOM overlay bounds
```

禁止:

- DOM button位置を別計算
- image transparent boundsをbutton boundsに利用
- animation中だけDOM位置が古い

Focus animation中:

- DOM button boundsをframeごとに同期、または
- animation中はspatial overlayを一時無効にし、selected summary sheetをfocus正本にする

どちらを採用するかprototypeで決める。

---

# 11. Runtime issue codes

追加候補:

```txt
RENDERER_SESSION_STALE
RENDERER_INIT_ABORTED
RENDERER_CONTEXT_LOST
RENDERER_CONTEXT_RESTORE_FAILED
ASSET_ALIAS_COLLISION
ASSET_MANIFEST_ACTIVATION_FAILED
ACCESSIBILITY_DUPLICATE_TARGET
FALLBACK_VISUAL_STALE
```

Private contentをissue detailへ含めない。

---

# 12. Required fixtures / tests before renderer implementation

- route leave during `Application.init()`
- route leave during asset load
- context loss during camera focus
- context restore with newer SceneSnapshot
- hidden tab start / stop
- motion off render-on-demand
- duplicate accessibility target detection
- overlay / list mode focus isolation
- fallback without WebGL
- stale cached snapshot label
- asset alias collision
- manifest version atomic switch
- repeated mount / unmount 100回

---

# Decision

```txt
PixiJSはvisual renderer。
DOMがinteraction / accessibilityの正本。

WebGLが失敗しても機能は残る。
非同期処理が遅れても古いsessionは復活しない。
一枚画像fallbackをdynamic Townの正確な正本とは呼ばない。
```
