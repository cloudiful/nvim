local M = {}

local config_root = vim.fn.stdpath("config")
local manifest
local warned = {}

local function load_manifest()
    if manifest ~= nil then
        return manifest
    end
    local path = vim.fs.joinpath(config_root, "tool-manifest.json")
    if vim.fn.filereadable(path) ~= 1 then
        manifest = false
        return manifest
    end
    local ok, value = pcall(vim.json.decode, table.concat(vim.fn.readfile(path), "\n"))
    manifest = ok and value or false
    return manifest
end

local function external_path(name)
    local path = vim.fn.exepath(name)
    if path ~= "" then
        return path
    end

    local mise = vim.fn.exepath("mise")
    if mise == "" then
        return nil
    end
    local result = vim.system({ mise, "which", name }, { text = true }):wait()
    if result.code == 0 then
        path = vim.trim(result.stdout or "")
        if path ~= "" and vim.fn.executable(path) == 1 then
            return path
        end
    end
    return nil
end

local function bundled_path(name, item)
    if not item or item.status ~= "bundled" or not item.path then
        return nil
    end
    local path = vim.fs.joinpath(config_root, item.path)
    local stat = vim.uv.fs_stat(path)
    if stat and (stat.type == "file" or stat.type == "link" or stat.type == "directory") then
        return path
    end
    return nil
end

function M.manifest()
    return load_manifest()
end

function M.status(name)
    local current = load_manifest()
    local item = current and current.tools and current.tools[name]
    return item and item.status or "external"
end

function M.resolve(name)
    local current = load_manifest()
    local item = current and current.tools and current.tools[name]
    local path = external_path(name)
    if path then
        return path, "external"
    end
    path = bundled_path(name, item)
    if path then
        return path, "bundled"
    end
    return nil, item and item.status or "external"
end

function M.command(name, args)
    local path, status = M.resolve(name)
    if not path then
        return nil, status
    end
    local command = { path }
    for _, argument in ipairs(args or {}) do
        command[#command + 1] = argument
    end
    return command, status
end

function M.explain(name)
    local path, status = M.resolve(name)
    if path or warned[name] then
        return path
    end
    warned[name] = true
    vim.notify(
        ("Tool %s is %s; install it externally or use a compatible full bundle"):format(name, status),
        vim.log.levels.WARN
    )
    return nil
end

function M.vue_plugin()
    local current = load_manifest()
    local item = current and current.tools and current.tools["@vue/typescript-plugin"]
    local bundled = bundled_path("@vue/typescript-plugin", item)
    if bundled then
        return bundled
    end

    local node = M.resolve("node")
    if not node then
        return nil
    end
    local result = vim.system({
        node,
        "-e",
        "process.stdout.write(require.resolve('@vue/typescript-plugin/package.json'))",
    }, { text = true, cwd = vim.fn.getcwd() }):wait()
    if result.code ~= 0 then
        return nil
    end
    return vim.fn.fnamemodify(vim.trim(result.stdout or ""), ":h")
end

return M
