local M = {}

local fallback_tools = {
    "stylua",
    "rustfmt",
    "gofmt",
    "shfmt",
    "prettier",
    "prettierd",
    "lua-language-server",
    "rust-analyzer",
    "bash-language-server",
    "docker-langserver",
    "docker-compose-langserver",
    "vscode-json-language-server",
    "yaml-language-server",
    "vscode-css-language-server",
    "tombi",
    "vtsls",
    "vue-language-server",
    "@vue/typescript-plugin",
    "node",
    "nu",
    "hyprls",
}

local function sorted_keys(t)
    local keys = {}
    for name in pairs(t) do
        keys[#keys + 1] = name
    end
    table.sort(keys)
    return keys
end

local function report_tool(tools, name, manifest_item)
    if name == "@vue/typescript-plugin" then
        local plugin_path = tools.vue_plugin()
        if plugin_path then
            vim.health.ok(("@vue/typescript-plugin: %s"):format(plugin_path))
        else
            vim.health.warn(
                "Tool @vue/typescript-plugin is external; install it externally or use a compatible full bundle",
                "Install the workspace `@vue/typescript-plugin` package, or use a full bundle that contains it."
            )
        end
        return
    end

    local path, actual = tools.resolve(name)
    if path then
        vim.health.ok(("%s: %s (%s)"):format(name, path, actual))
        return
    end

    local status = manifest_item and manifest_item.status or tools.status(name)
    local reason = manifest_item and manifest_item.reason or nil
    local message = tools.message(name, status)
    if reason and reason ~= "" then
        message = message .. " (" .. reason .. ")"
    end
    if status == "bundled" then
        vim.health.error(
            message,
            "Reinstall the full bundle for this target, or install the tool externally via PATH or `mise`."
        )
    elseif status == "unsupported" then
        vim.health.info(message .. " (no compatible asset for this target)")
    else
        vim.health.warn(
            message,
            "Install it externally via PATH or `mise`, or use a compatible full bundle containing tool-manifest.json."
        )
    end
end

function M.check()
    local ok, tools = pcall(require, "tool_resolver")
    if not ok then
        vim.health.start("tool_resolver")
        vim.health.error("could not load tool_resolver")
        return
    end

    vim.health.start("tool_resolver")
    local manifest = tools.manifest()
    if manifest == false or manifest == nil then
        vim.health.info("tool-manifest.json not found (core profile); resolving from PATH and `mise`.")
        for _, name in ipairs(fallback_tools) do
            report_tool(tools, name, nil)
        end
        return
    end

    vim.health.info(("profile: %s target: %s"):format(manifest.profile or "?", manifest.target or "?"))
    local names = sorted_keys(manifest.tools or {})
    if #names == 0 then
        vim.health.info("manifest contains no tools.")
        return
    end
    for _, name in ipairs(names) do
        report_tool(tools, name, manifest.tools[name])
    end
end

return M
