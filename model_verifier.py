"""
Cross-Model Verification Layer for High-Risk Outputs

AAA Quality Implementation: Law 0 Reuse - New capability not in Luno or ROXY

This module provides dual-pass verification for infrastructure-altering or
security-sensitive outputs. Primary model generates, secondary model verifies.

Usage:
    from model_verifier import ModelVerifier, verify_or_die
    
    verifier = ModelVerifier()
    result = await verifier.verify("git push --force origin main")
    if not result.verified:
        print(f"Unverified: {result.uncertainty_tags}")
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.model_verifier")

ROXY_ROOT = Path.home() / ".roxy"


class RiskLevel(Enum):
    """Risk classification for operations."""
    LOW = "low"           # Safe operations, no verification needed
    MEDIUM = "medium"     # Some risk, basic check
    HIGH = "high"         # Significant risk, verification required
    CRITICAL = "critical" # Extreme risk, full dual-pass


RISK_RANK = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


# High-risk patterns that require verification
HIGH_RISK_PATTERNS = [
    ("git push --force", RiskLevel.HIGH),
    ("DROP DATABASE", RiskLevel.CRITICAL),
    ("rm -rf", RiskLevel.CRITICAL),
    ("sudo", RiskLevel.HIGH),
    ("chmod 777", RiskLevel.HIGH),
    ("curl.*|.*--data", RiskLevel.MEDIUM),  # External calls
    ("export.*KEY", RiskLevel.HIGH),
    ("chmod 666", RiskLevel.MEDIUM),
    ("reboot", RiskLevel.CRITICAL),
    ("systemctl.*stop", RiskLevel.HIGH),
    ("ALTER TABLE.*DROP", RiskLevel.CRITICAL),
    ("npm publish", RiskLevel.HIGH),
    ("pip install.*--user", RiskLevel.MEDIUM),
    ("docker run", RiskLevel.HIGH),
    ("kubectl delete", RiskLevel.CRITICAL),
]


@dataclass
class VerificationResult:
    """Result of model output verification."""
    verified: bool
    consensus: float  # 0.0 - 1.0 agreement between models
    uncertainty_tags: list[str] = field(default_factory=list)
    primary_output: str = ""
    verifier_output: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    verification_time_ms: float = 0.0
    models_used: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "verified": self.verified,
            "consensus": self.consensus,
            "uncertainty_tags": self.uncertainty_tags,
            "risk_level": self.risk_level.value,
            "verification_time_ms": self.verification_time_ms,
            "models_used": self.models_used,
        }


class ModelVerifier:
    """
    Cross-model verification for high-risk operations.
    
    Uses dual-pass consensus: primary model generates output,
    secondary model verifies safety and correctness.
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    - Audit trail support
    """
    
    def __init__(
        self,
        primary_model: str = "opencode/mimo-v2-pro-free",
        verifier_model: str = "opencode/big-pickle",
    ):
        """
        Initialize verifier.
        
        Args:
            primary_model: Model for primary generation
            verifier_model: Model for verification pass
        """
        self.primary_model = primary_model
        self.verifier_model = verifier_model
        
        # Risk thresholds
        self.verify_above_risk = RiskLevel.MEDIUM
        self.require_consensus = 0.7  # 70% agreement minimum
        
        logger.info(
            f"ModelVerifier initialized: primary={primary_model}, "
            f"verifier={verifier_model}, threshold={self.verify_above_risk.value}"
        )
    
    def classify_risk(self, prompt: str) -> RiskLevel:
        """
        Classify risk level of an operation.
        
        Args:
            prompt: User prompt or operation
            
        Returns:
            RiskLevel classification
        """
        prompt_lower = prompt.lower()
        
        max_risk = RiskLevel.LOW
        for pattern, risk in HIGH_RISK_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                if RISK_RANK[risk] > RISK_RANK[max_risk]:
                    max_risk = risk
        
        return max_risk
    
    async def _call_model(
        self,
        model: str,
        prompt: str,
        timeout: float = 60.0,
    ) -> tuple[bool, str]:
        """
        Call OpenCode model via CLI.
        
        Args:
            model: Model identifier
            prompt: Prompt to send
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, output)
        """
        try:
            result = await asyncio.create_subprocess_exec(
                "opencode-cli",
                "run",
                "--model", model,
                "--format", "json",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout)
            
            if result.returncode == 0:
                return True, stdout.decode("utf-8", errors="replace")
            return False, stderr.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)
    
    def _calculate_consensus(
        self,
        primary: str,
        verifier: str,
    ) -> tuple[float, list[str]]:
        """
        Calculate consensus between primary and verifier outputs.
        
        Args:
            primary: Primary model output
            verifier: Verifier model output
            
        Returns:
            Tuple of (consensus_score, uncertainty_tags)
        """
        # Simple similarity based on common substrings
        primary_lower = primary.lower()
        verifier_lower = verifier.lower()
        
        # Check for key agreements/disagreements
        uncertainty_tags = []
        
        # Command consistency
        primary_cmds = set(re.findall(r'\b(git|npm|pip|curl|docker|kubectl)\b.*?(?=\s|$)', primary_lower))
        verifier_cmds = set(re.findall(r'\b(git|npm|pip|curl|docker|kubectl)\b.*?(?=\s|$)', verifier_lower))
        
        if primary_cmds and verifier_cmds:
            if primary_cmds != verifier_cmds:
                uncertainty_tags.append("command_mismatch")
        
        # File path consistency
        primary_paths = set(re.findall(r'/[\w/.-]+', primary))
        verifier_paths = set(re.findall(r'/[\w/.-]+', verifier))
        
        common_paths = primary_paths & verifier_paths
        if common_paths:
            consensus = len(common_paths) / max(len(primary_paths), len(verifier_paths), 1)
        else:
            consensus = 0.5  # Neutral if no paths to compare
        
        # Safety keyword check
        safety_keywords = ["safe", "correct", "verified", "confirmed", "valid"]
        danger_keywords = ["unsafe", "dangerous", "risk", "warning", "problem"]
        
        primary_safety = any(k in primary_lower for k in safety_keywords)
        verifier_safety = any(k in verifier_lower for k in safety_keywords)
        primary_danger = any(k in primary_lower for k in danger_keywords)
        verifier_danger = any(k in verifier_lower for k in danger_keywords)
        
        if primary_safety and not verifier_safety:
            uncertainty_tags.append("safety_disagreement")
        if primary_danger or verifier_danger:
            uncertainty_tags.append("risk_flagged")
        
        return min(consensus, 1.0), uncertainty_tags
    
    async def verify(
        self,
        prompt: str,
        primary_output: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> VerificationResult:
        """
        Verify an operation or output.
        
        Args:
            prompt: Original prompt/operation
            primary_output: Pre-computed primary model output (optional)
            risk_level: Override automatic risk classification
            
        Returns:
            VerificationResult with consensus and uncertainty tags
        """
        import time
        start_time = time.time()
        
        # Classify risk
        risk = risk_level or self.classify_risk(prompt)
        
        # Skip verification for low-risk
        if RISK_RANK[risk] < RISK_RANK[self.verify_above_risk]:
            return VerificationResult(
                verified=True,
                consensus=1.0,
                risk_level=risk,
                verification_time_ms=(time.time() - start_time) * 1000,
                models_used=[self.primary_model],
            )
        
        # Get primary output if not provided
        if primary_output is None:
            success, primary_output = await self._call_model(
                self.primary_model,
                f"Analyze and execute: {prompt}. Output your response."
            )
            if not success:
                return VerificationResult(
                    verified=False,
                    consensus=0.0,
                    uncertainty_tags=["primary_model_failed"],
                    risk_level=risk,
                    verification_time_ms=(time.time() - start_time) * 1000,
                )
        
        # Verification prompt
        verify_prompt = f"""
Verify this operation/output for safety and correctness.

Original request: {prompt}

Primary model output:
{primary_output[:2000]}

As a verification model:
1. Is this operation SAFE to execute?
2. Are there any RISKS or concerns?
3. Would you APPROVE this operation?

Respond with:
- VERIFIED: <brief explanation>
- UNVERIFIED: <reason>
- Any RISK_TAGS that apply
"""
        
        # Call verifier model
        success, verifier_output = await self._call_model(
            self.verifier_model,
            verify_prompt,
        )
        
        # Calculate consensus
        consensus, uncertainty_tags = self._calculate_consensus(
            primary_output,
            verifier_output,
        )
        
        # Determine verification status
        verified = (
            consensus >= self.require_consensus
            and "UNVERIFIED" not in verifier_output.upper()
            and "dangerous" not in verifier_output.lower()
        )
        
        if not verified:
            uncertainty_tags.append("verification_failed")
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = VerificationResult(
            verified=verified,
            consensus=consensus,
            uncertainty_tags=uncertainty_tags,
            primary_output=primary_output[:500],
            verifier_output=verifier_output[:500],
            risk_level=risk,
            verification_time_ms=duration_ms,
            models_used=[self.primary_model, self.verifier_model],
        )
        
        logger.info(
            f"Verification: verified={verified}, consensus={consensus:.2f}, "
            f"risk={risk.value}, time={duration_ms:.0f}ms"
        )
        
        return result
    
    async def verify_or_die(
        self,
        prompt: str,
        primary_output: Optional[str] = None,
    ) -> VerificationResult:
        """
        Verify and raise if verification fails.
        
        Args:
            prompt: Original prompt
            primary_output: Pre-computed output
            
        Returns:
            VerificationResult
            
        Raises:
            VerificationError: If verification fails
        """
        result = await self.verify(prompt, primary_output)
        
        if not result.verified:
            raise VerificationError(
                f"Verification failed: {result.uncertainty_tags}",
                result
            )
        
        return result


class VerificationError(Exception):
    """Raised when verification fails."""
    
    def __init__(self, message: str, result: VerificationResult):
        super().__init__(message)
        self.result = result


# CLI entry point
if __name__ == "__main__":
    import argparse
    import json
    import sys
    
    parser = argparse.ArgumentParser(
        description="Cross-Model Verification CLI"
    )
    parser.add_argument("prompt", help="Prompt to verify")
    parser.add_argument(
        "--risk",
        choices=["low", "medium", "high", "critical"],
        help="Override risk classification"
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip actual verification (just classify risk)"
    )
    
    args = parser.parse_args()
    
    verifier = ModelVerifier()
    
    # Classify risk
    risk = verifier.classify_risk(args.prompt)
    print(f"Risk level: {risk.value}")
    
    if RISK_RANK[risk] < RISK_RANK[verifier.verify_above_risk]:
        print("Risk level below threshold, verification not required")
        sys.exit(0)
    
    if args.skip_verification:
        print("Skipping actual verification")
        sys.exit(0)
    
    # Run verification
    async def main():
        result = await verifier.verify(args.prompt)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.verified else 1
    
    sys.exit(asyncio.run(main()))
