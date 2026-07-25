local root = assert(vim.env.NVIM_SOURCE_ROOT, "NVIM_SOURCE_ROOT is required")

vim.opt.runtimepath:prepend(root)
package.path = root .. "/lua/?.lua;" .. package.path

vim.pack.add(require("plugin_specs").all(), {
  confirm = false,
  load = false,
})
