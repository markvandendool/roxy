"""
Sprint 4 Tests - Dashboard, Help, Deploy
Part of ROCKY-ROXY-ROCKIN-V1: Sprint 4 - Polish & Launch

Stories: RRR-015, RRR-016, RRR-017, RRR-018
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════
# RRR-015: Dashboard Tests
# ═══════════════════════════════════════════════════════════════

class TestDashboard:
    """Dashboard component tests"""
    
    def test_dashboard_file_exists(self):
        """Dashboard component file exists"""
        dashboard_path = Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx"
        assert dashboard_path.exists(), "Dashboard.tsx should exist"
    
    def test_dashboard_has_service_definitions(self):
        """Dashboard defines all required services"""
        dashboard_path = Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx"
        content = dashboard_path.read_text()
        
        required_services = [
            "ROXY Core",
            "Luno Orchestrator",
            "n8n",
            "ChromaDB",
            "Ollama",
            "Whisper",
            "Piper",
            "Friday"
        ]
        
        for service in required_services:
            assert service in content, f"Dashboard should include {service}"
    
    def test_dashboard_has_metrics(self):
        """Dashboard includes metrics tracking"""
        dashboard_path = Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx"
        content = dashboard_path.read_text()
        
        assert "DashboardMetrics" in content, "Dashboard should have metrics interface"
        assert "totalTools" in content, "Dashboard should track total tools"
        assert "modeToggles" in content, "Dashboard should track mode toggles"
    
    def test_dashboard_health_ring(self):
        """Dashboard has health visualization"""
        dashboard_path = Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx"
        content = dashboard_path.read_text()
        
        assert "health-ring" in content, "Dashboard should have health ring"
        assert "healthPercent" in content, "Dashboard should calculate health percent"
    
    def test_dashboard_quick_actions(self):
        """Dashboard has quick action buttons"""
        dashboard_path = Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx"
        content = dashboard_path.read_text()
        
        assert "Quick Actions" in content, "Dashboard should have quick actions"
        assert "Omnibar" in content, "Dashboard should mention Omnibar"
        assert "Toggle Mode" in content, "Dashboard should mention mode toggle"


# ═══════════════════════════════════════════════════════════════
# RRR-016: Help System Tests
# ═══════════════════════════════════════════════════════════════

class TestHelpSystem:
    """Help panel tests"""
    
    def test_help_panel_exists(self):
        """Help panel file exists"""
        help_path = Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx"
        assert help_path.exists(), "HelpPanel.tsx should exist"
    
    def test_keyboard_shortcuts_defined(self):
        """Help panel defines keyboard shortcuts"""
        help_path = Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx"
        content = help_path.read_text()
        
        assert "KEYBOARD_SHORTCUTS" in content, "Help should define shortcuts"
        assert "⌘" in content, "Help should include Command key"
        assert "F1" in content, "Help should include F1 key"
    
    def test_help_has_tabs(self):
        """Help panel has multiple tabs"""
        help_path = Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx"
        content = help_path.read_text()
        
        assert "shortcuts" in content, "Help should have shortcuts tab"
        assert "tools" in content, "Help should have tools tab"
        assert "about" in content, "Help should have about tab"
    
    def test_help_documents_tools(self):
        """Help panel documents MCP tools"""
        help_path = Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx"
        content = help_path.read_text()
        
        assert "rocky_" in content, "Help should document Rocky tools"
        assert "orchestrator_" in content, "Help should document orchestrator tools"
        assert "cp_" in content or "voice_" in content, "Help should document cross-pollination or voice tools"
    
    def test_help_hook_exists(self):
        """useHelpPanel hook is defined"""
        help_path = Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx"
        content = help_path.read_text()
        
        assert "useHelpPanel" in content, "useHelpPanel hook should be defined"
        assert "isOpen" in content, "Hook should track open state"


# ═══════════════════════════════════════════════════════════════
# RRR-017: Deploy Scripts Tests
# ═══════════════════════════════════════════════════════════════

class TestDeployScripts:
    """Deployment scripts tests"""
    
    def test_launch_script_exists(self):
        """Launch script exists"""
        launch_path = Path.home() / ".roxy/roxy-launch.sh"
        assert launch_path.exists(), "roxy-launch.sh should exist"
    
    def test_launch_script_executable(self):
        """Launch script is executable"""
        launch_path = Path.home() / ".roxy/roxy-launch.sh"
        assert os.access(launch_path, os.X_OK), "roxy-launch.sh should be executable"
    
    def test_launch_script_commands(self):
        """Launch script has all required commands"""
        launch_path = Path.home() / ".roxy/roxy-launch.sh"
        content = launch_path.read_text()
        
        commands = ["start", "stop", "restart", "status", "logs", "health"]
        for cmd in commands:
            assert f"cmd_{cmd}" in content or f'"{cmd}")' in content, f"Launch script should support {cmd} command"
    
    def test_systemd_service_exists(self):
        """Systemd service file exists"""
        service_path = Path.home() / ".roxy/systemd/roxy-core.service"
        assert service_path.exists(), "roxy-core.service should exist"
    
    def test_systemd_service_valid(self):
        """Systemd service file has required sections"""
        service_path = Path.home() / ".roxy/systemd/roxy-core.service"
        content = service_path.read_text()
        
        assert "[Unit]" in content, "Service should have Unit section"
        assert "[Service]" in content, "Service should have Service section"
        assert "[Install]" in content, "Service should have Install section"
        assert "ExecStart" in content, "Service should have ExecStart"
    
    def test_health_monitor_exists(self):
        """Health monitor script exists"""
        monitor_path = Path.home() / ".roxy/health_monitor.py"
        assert monitor_path.exists(), "health_monitor.py should exist"


# ═══════════════════════════════════════════════════════════════
# Health Monitor Tests
# ═══════════════════════════════════════════════════════════════

class TestHealthMonitor:
    """Health monitor functionality tests"""
    
    def test_health_monitor_imports(self):
        """Health monitor can be imported"""
        from health_monitor import HealthMonitor, ServiceConfig, ServiceStatus
        assert HealthMonitor is not None
        assert ServiceConfig is not None
        assert ServiceStatus is not None
    
    def test_service_config_creation(self):
        """ServiceConfig can be created"""
        from health_monitor import ServiceConfig
        
        config = ServiceConfig(
            name="Test Service",
            endpoint="http://localhost:8000/health",
            port=8000
        )
        
        assert config.name == "Test Service"
        assert config.port == 8000
        assert config.critical is True  # default
    
    def test_health_monitor_creation(self):
        """HealthMonitor can be created"""
        from health_monitor import HealthMonitor, ServiceConfig
        
        services = [
            ServiceConfig(name="Test", endpoint="http://localhost:8000", port=8000)
        ]
        
        monitor = HealthMonitor(services, check_interval=60.0)
        
        assert len(monitor.services) == 1
        assert "Test" in monitor.states
    
    def test_status_enum_values(self):
        """ServiceStatus has expected values"""
        from health_monitor import ServiceStatus
        
        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.OFFLINE.value == "offline"
        assert ServiceStatus.UNKNOWN.value == "unknown"
    
    def test_monitor_get_summary(self):
        """Monitor can produce summary"""
        from health_monitor import HealthMonitor, ServiceConfig, ServiceStatus
        
        services = [
            ServiceConfig(name="Test1", endpoint="http://localhost:8001", port=8001),
            ServiceConfig(name="Test2", endpoint="http://localhost:8002", port=8002),
        ]
        
        monitor = HealthMonitor(services)
        summary = monitor.get_summary()
        
        assert "total_services" in summary
        assert summary["total_services"] == 2
        assert "healthy" in summary
        assert "offline" in summary


# ═══════════════════════════════════════════════════════════════
# RRR-018: Final Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestFinalIntegration:
    """Final integration verification"""
    
    def test_all_sprint1_files_exist(self):
        """Sprint 1 MCP bridge files exist"""
        roxy_home = Path.home() / ".roxy"
        
        required_files = [
            "mcp/mcp_orchestrator.py",
            "mcp/mcp_rocky.py",
            "mcp/mcp_n8n.py",
            "mcp/mcp_voice.py",
        ]
        
        for file in required_files:
            path = roxy_home / file
            assert path.exists(), f"Sprint 1 file should exist: {file}"
    
    def test_all_sprint2_files_exist(self):
        """Sprint 2 UI files exist"""
        jukehub = Path.home() / "mindsong-juke-hub/src"
        
        required_files = [
            "contexts/CommandCenterContext.tsx",
            "components/command-center/ModeToggle.tsx",
            "components/command-center/Omnibar.tsx",
        ]
        
        for file in required_files:
            path = jukehub / file
            assert path.exists(), f"Sprint 2 file should exist: {file}"
    
    def test_all_sprint3_files_exist(self):
        """Sprint 3 cross-pollination files exist"""
        roxy_home = Path.home() / ".roxy"
        
        required_files = [
            "cross_pollination.py",
            "mcp/mcp_cross_pollination.py",
        ]
        
        for file in required_files:
            path = roxy_home / file
            assert path.exists(), f"Sprint 3 file should exist: {file}"
    
    def test_all_sprint4_files_exist(self):
        """Sprint 4 files exist"""
        required = [
            Path.home() / "mindsong-juke-hub/src/components/command-center/Dashboard.tsx",
            Path.home() / "mindsong-juke-hub/src/components/command-center/HelpPanel.tsx",
            Path.home() / ".roxy/roxy-launch.sh",
            Path.home() / ".roxy/systemd/roxy-core.service",
            Path.home() / ".roxy/health_monitor.py",
        ]
        
        for path in required:
            assert path.exists(), f"Sprint 4 file should exist: {path}"
    
    def test_total_mcp_tools_count(self):
        """Verify we have comprehensive MCP tools"""
        roxy_home = Path.home() / ".roxy"
        
        tool_files = [
            "mcp/mcp_orchestrator.py",
            "mcp/mcp_rocky.py",
            "mcp/mcp_n8n.py",
            "mcp/mcp_voice.py",
            "mcp/mcp_cross_pollination.py",
        ]
        
        existing_count = 0
        for file in tool_files:
            path = roxy_home / file
            if path.exists():
                existing_count += 1
                content = path.read_text()
                # Verify each file has tool definitions
                assert "def " in content, f"{file} should have function definitions"
        
        # All 5 MCP bridge files should exist
        assert existing_count == 5, f"Should have 5 MCP bridge files, found {existing_count}"


# ═══════════════════════════════════════════════════════════════
# Epic Completion Verification
# ═══════════════════════════════════════════════════════════════

class TestEpicCompletion:
    """ROCKY-ROXY-ROCKIN-V1 Epic verification"""
    
    def test_epic_directory_structure(self):
        """Epic has proper directory structure"""
        roxy_home = Path.home() / ".roxy"
        
        required_dirs = [
            "mcp",
            "tests",
            "logs",
            "systemd",
        ]
        
        for dir_name in required_dirs:
            path = roxy_home / dir_name
            assert path.exists() or dir_name == "logs", f"Directory should exist: {dir_name}"
    
    def test_ui_component_structure(self):
        """UI components have proper structure"""
        cc_dir = Path.home() / "mindsong-juke-hub/src/components/command-center"
        
        required_components = [
            "ModeToggle.tsx",
            "Omnibar.tsx",
            "Dashboard.tsx",
            "HelpPanel.tsx",
        ]
        
        for component in required_components:
            path = cc_dir / component
            assert path.exists(), f"Component should exist: {component}"
    
    def test_cross_pollination_complete(self):
        """Cross-pollination module is complete"""
        cp_path = Path.home() / ".roxy/cross_pollination.py"
        content = cp_path.read_text()
        
        required_classes = [
            "RockyEnhancedOrchestrator",
            "RockyWorkflowTriggers",
            "CitadelNotifier",
            "UnifiedKnowledgeBase",
            "FridaySyncProtocol",
            "CrossPollinator",
        ]
        
        for cls in required_classes:
            assert cls in content, f"CrossPollination should have {cls}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
