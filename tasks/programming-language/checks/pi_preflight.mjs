/** Free regression check using pinned Pi's loader, tool wrappers, and agent loop.
 * Usage: node checks/pi_preflight.mjs /path/to/@earendil-works/pi-coding-agent
 * No credentials or provider calls. Node/Pi are optional development tools.
 */
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const task = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const pkg = resolve(process.argv[2]);
const version = JSON.parse(await readFile(join(pkg, "package.json"), "utf8")).version;
assert.equal(version, "0.85.1");
const moduleAt = (path) => import(pathToFileURL(join(pkg, path)).href);
const { loadExtensions } = await moduleAt("dist/core/extensions/loader.js");
const { wrapRegisteredTools } = await moduleAt("dist/core/extensions/wrapper.js");
const { SessionManager } = await moduleAt("dist/core/session-manager.js");
const { createReadToolDefinition, createBashToolDefinition,
  createEditToolDefinition, createWriteToolDefinition } = await moduleAt("dist/index.js");
const { Agent } = await moduleAt("node_modules/@earendil-works/pi-agent-core/dist/agent.js");
const { AssistantMessageEventStream } = await moduleAt(
  "node_modules/@earendil-works/pi-ai/dist/utils/event-stream.js");
const { getModel } = await moduleAt("node_modules/@earendil-works/pi-ai/dist/compat.js");
const model = getModel("google", "gemini-3.5-flash");
assert.equal(model.id, "gemini-3.5-flash");
assert.deepEqual(model.cost, { input: 1.5, output: 9, cacheRead: 0.15, cacheWrite: 0 });
// Fail closed if any accidental HTTP call is introduced into this scripted check.
globalThis.fetch = () => { throw new Error("Network forbidden in offline Pi preflight"); };

const cwd = await mkdtemp(join(tmpdir(), "language-pi-tools-"));
try {
  const loaded = await loadExtensions([join(task, "language_agent/sequential-tools.ts")], cwd);
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const registered = [...loaded.extensions[0].tools.values()];
  const native = [createReadToolDefinition, createBashToolDefinition,
    createEditToolDefinition, createWriteToolDefinition].map((create) => create(cwd));
  assert.deepEqual(registered.map(({ definition }) => definition.name), native.map(t => t.name));
  for (const { definition } of registered) {
    const original = native.find(t => t.name === definition.name);
    assert.equal(definition.executionMode, "sequential");
    for (const key of ["description", "parameters", "promptSnippet", "promptGuidelines"]) {
      assert.deepEqual(definition[key], original[key], `${definition.name}: ${key}`);
    }
  }
  const sessionManager = SessionManager.inMemory(cwd);
  const runner = { createContext: () => ({ cwd, sessionManager }),
    getActiveTools: () => native.map(t => t.name) };
  const tools = wrapRegisteredTools(registered, runner);
  // Run the actual seeded interpreter on whichever source the bash tool opens.
  await writeFile(join(cwd, "probe.py"), `import json, sys\nfrom pathlib import Path\n` +
    `sys.path.insert(0, ${JSON.stringify(join(task, "environment"))})\n` +
    `from language_game.engine import Language, compile_source, execute\n` +
    `from language_game.generation import generate_trial\n` +
    `language = Language(**generate_trial(17)['language'])\n` +
    `source = Path('solution.lang').read_text()\n` +
    `result = execute(language, compile_source(language, source), [0])\n` +
    `print(json.dumps({'source': source, 'output': result.output, 'error': result.error}))\n`);
  const calls = [];
  const call = (name, args) => calls.push({ type: "toolCall", id: `call-${calls.length}`, name, arguments: args });
  for (const source of ["egh", "efh", "eh"]) {
    call("write", { path: "solution.lang", content: source });
    call("bash", { command: "python3 probe.py" });
  }
  call("edit", { path: "solution.lang", oldText: "eh", newText: "egh" });
  call("read", { path: "solution.lang" });
  // Bash can also mutate the shared file, so write-only serialization is insufficient.
  call("bash", { command: "printf efh > solution.lang" });
  call("bash", { command: "python3 probe.py" });
  let turns = 0;
  const streamFn = () => {
    const stream = new AssistantMessageEventStream();
    const content = turns++ === 0 ? calls : [{ type: "text", text: "done" }];
    const message = { role: "assistant", content, api: model.api, provider: model.provider,
      model: model.id, timestamp: 0, stopReason: turns === 1 ? "toolUse" : "stop",
      usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } } };
    stream.push({ type: "done", reason: message.stopReason, message });
    return stream;
  };
  const agent = new Agent({ initialState: { model, tools }, streamFn });
  assert.equal(agent.toolExecution, "parallel"); // The extension must override the real default.
  let active = 0;
  let maximumActive = 0;
  const completed = [];
  agent.subscribe(event => {
    if (event.type === "tool_execution_start") maximumActive = Math.max(maximumActive, ++active);
    if (event.type === "tool_execution_end") { active--; completed.push(event); }
  });
  await agent.prompt("Execute the scripted regression probes.");
  assert.equal(turns, 2);
  assert.equal(maximumActive, 1);
  assert.equal(active, 0);
  assert.deepEqual(completed.map(e => e.toolCallId), calls.map(c => c.id));
  assert.ok(completed.every(e => !e.isError), JSON.stringify(completed));
  const outputs = [1, 3, 5, 9].map(index => JSON.parse(completed[index].result.content[0].text));
  assert.deepEqual(outputs, [
    { source: "egh", output: [1], error: null },
    { source: "efh", output: [31], error: null },
    { source: "eh", output: [0], error: null },
    { source: "efh", output: [31], error: null },
  ]);
  assert.equal(completed[7].result.content[0].text, "egh");
  console.log(JSON.stringify({ passed: true, piVersion: version, model: model.id,
    nativeTools: tools.map(t => t.name), orderedCalls: completed.length, maximumActive,
    interpreterOutputs: outputs, modelApiCalls: 0 }, null, 2));
} finally {
  await rm(cwd, { recursive: true, force: true });
}
