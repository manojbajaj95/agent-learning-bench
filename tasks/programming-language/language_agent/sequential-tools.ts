/** Preserve native Pi tools and prompts, executing assistant tool batches in order. */
import {
  type ExtensionAPI,
  createBashToolDefinition,
  createEditToolDefinition,
  createReadToolDefinition,
  createWriteToolDefinition,
} from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  for (const create of [
    createReadToolDefinition,
    createBashToolDefinition,
    createEditToolDefinition,
    createWriteToolDefinition,
  ]) {
    pi.registerTool({ ...create(process.cwd()), executionMode: "sequential" });
  }
}
