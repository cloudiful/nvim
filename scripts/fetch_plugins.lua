local root = assert(vim.env.NVIM_SOURCE_ROOT, "NVIM_SOURCE_ROOT is required")

vim.opt.runtimepath:prepend(root)
package.path = root .. "/lua/?.lua;" .. package.path

local lock_path = vim.fs.joinpath(root, "nvim-pack-lock.json")
local lock = vim.json.decode(table.concat(vim.fn.readfile(lock_path), "\n"))
local specs = require("plugin_specs").all()

for _, spec in ipairs(specs) do
  local locked = assert(lock.plugins[spec.name], "Missing lock entry: " .. spec.name)
  assert(locked.src == spec.src, "Lock source mismatch: " .. spec.name)
  assert(type(locked.rev) == "string" and locked.rev ~= "", "Missing lock revision: " .. spec.name)

  vim.pack.add({
    vim.tbl_extend("force", spec, { version = locked.rev }),
  }, {
    confirm = false,
    load = false,
  })
end
