<project>
  <context>
    Secure Docker environments for AI-assisted coding with network isolation.
  </context>

  <quick-start>
    <installation>
      <command>pip install -e .</command>
      <command>ai-sbx init global --wizard</command>
      <alternative>ai-sbx init global</alternative>
    </installation>

    <project-setup>
      <command>cd /your/project</command>
      <command>ai-sbx init project</command>
      <wizard-features>
        <feature>Detect Claude settings (~/.claude/) and offer to include them</feature>
        <feature>Configure network isolation and proxy</feature>
        <feature>Create .devcontainer for your IDE</feature>
      </wizard-features>
    </project-setup>

    <task-workflow>
      <command>ai-sbx worktree create "implement user authentication"</command>
      <ide-integration>Open in IDE (VS Code: "Reopen in Container", PyCharm: Docker Compose interpreter)</ide-integration>
      <cleanup>ai-sbx worktree remove</cleanup>
    </task-workflow>
  </quick-start>

  <commands>
    <command name="init global --wizard">Interactive setup with detailed reporting</command>
    <command name="init project">Setup project with devcontainer</command>
    <command name="worktree create">Create task workspace</command>
    <command name="worktree list">List workspaces</command>
    <command name="worktree remove">Remove workspace</command>
    <command name="doctor --verbose">Detailed system analysis</command>
    <command name="doctor --fix">Fix common issues</command>
  </commands>

  <init-global-reporting>
    <report-item>Directories created with full paths</report-item>
    <report-item>Files created or modified</report-item>
    <report-item>Docker images built</report-item>
    <report-item>System groups created</report-item>
    <report-item>User modifications</report-item>
    <report-item>Docker containers started</report-item>
    <report-item>Any errors encountered</report-item>
  </init-global-reporting>

  <security>
    <built-in-protections>
      <protection>Non-root container (user: claude)</protection>
      <protection>Network isolation (internal network)</protection>
      <protection>Proxy filtering (whitelisted domains only)</protection>
      <protection>No SSH, sudo, or passwords</protection>
    </built-in-protections>

    <restrictions>
      <restriction>Never add sudo or root access</restriction>
      <restriction>Never disable network isolation</restriction>
      <restriction>Never bypass proxy settings</restriction>
    </restrictions>
  </security>

  <ide-setup>
    <vscode>
      <instruction>Open folder → "Reopen in Container" when prompted</instruction>
    </vscode>

    <pycharm>
      <instruction>Settings → Python Interpreter → Add → Docker Compose</instruction>
      <setting name="service">devcontainer</setting>
      <setting name="python-path">/usr/local/bin/python</setting>
    </pycharm>

    <claude-code>
      <command>claude --dangerously-skip-permissions</command>
    </claude-code>
  </ide-setup>

  <claude-settings>
    <detection>During project setup, detects ~/.claude/ on host</detection>
    <features>
      <feature>CLI detects agents, commands, and hooks</feature>
      <feature>Option to mount them readonly in container</feature>
      <feature>Settings copied on container startup (originals safe)</feature>
    </features>
  </claude-settings>

  <custom-registry>
    <configuration-time>During ai-sbx init global --wizard</configuration-time>
    <capabilities>
      <capability>Configure custom Docker registries for caching</capability>
      <capability>Specify custom docker-registry-proxy image with CA certificates</capability>
      <capability>Automatically creates .env file at ~/.ai-sbx/docker-proxy/.env</capability>
    </capabilities>

    <example>
      <registries>registry1.company.com,registry2.local</registries>
      <proxy-image>myregistry/docker-registry-proxy:custom-ca</proxy-image>
    </example>
  </custom-registry>

  <diagnostics>
    <command>ai-sbx doctor --verbose</command>
    <reports>
      <report>AI Agents Sandbox directories with permissions and sizes</report>
      <report>Configuration files status</report>
      <report>Docker containers state</report>
      <report>System groups and members</report>
      <report>Detailed issue analysis</report>
    </reports>
  </diagnostics>

  <troubleshooting>
    <issue problem="Container can't access a site">
      <solution>Add domain to .devcontainer/ai-sbx.yaml whitelist</solution>
      <solution>Run ai-sbx init update</solution>
    </issue>

    <issue problem="IDE can't connect">
      <solution>Check Docker is running: docker ps</solution>
    </issue>

    <issue problem="Need upstream proxy">
      <solution>Configure in .devcontainer/ai-sbx.yaml</solution>
      <solution>Run ai-sbx init update</solution>
    </issue>

    <issue problem="Custom registry issues">
      <solution>Check ~/.ai-sbx/docker-proxy/.env exists and contains your registries</solution>
    </issue>
  </troubleshooting>

  <project-structure>
    <directory path=".devcontainer">
      <file name="ai-sbx.yaml">Your configuration (edit this)</file>
      <file name=".env">Auto-generated (don't edit)</file>
      <file name="docker-compose.yaml">Container setup</file>
    </directory>
  </project-structure>

  <documentation>
    <reference>For detailed documentation, see docs/ directory</reference>
  </documentation>
</project>