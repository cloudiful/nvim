local plugin_dir = assert(vim.env.BLINK_PLUGIN_DIR, "BLINK_PLUGIN_DIR is required")
local path = vim.fs.joinpath(plugin_dir, "lua", "blink", "cmp", "fuzzy", "download", "git.lua")
local content = table.concat(vim.fn.readfile(path), "\n")

local replacement = [[if not repo_dir then
      if force_version then return resolve(force_version) end
      return resolve()
    end]]
local patched, count = content:gsub(
  "if not repo_dir then resolve%(%) end",
  replacement,
  1
)
if count ~= 1 then
  error("Unexpected blink.cmp git.lua layout")
end

patched, count = patched:gsub(
  "if not repo_dir then resolve%(%) end",
  "if not repo_dir then return resolve() end",
  1
)
if count ~= 1 then
  error("Unexpected blink.cmp get_sha layout")
end

vim.fn.writefile(vim.split(patched, "\n", { plain = true }), path)
