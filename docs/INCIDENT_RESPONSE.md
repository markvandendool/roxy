# ROXY Incident Response Playbook

## Overview

This playbook outlines procedures for responding to security incidents and system failures.

## Incident Classification

### Severity Levels

- **P0 - Critical**: System down, data breach, security compromise
- **P1 - High**: Service degradation, partial outage
- **P2 - Medium**: Performance issues, non-critical errors
- **P3 - Low**: Minor issues, cosmetic problems

## Response Procedures

### P0 - Critical Incidents

#### System Down

1. **Immediate Actions**:
   ```bash
   # Check service status
   systemctl --user status roxy-core
   docker ps
   
   # Check logs
   journalctl --user -u roxy-core -n 100
   tail -100 ~/.roxy/logs/roxy_core.log
   ```

2. **Recovery Steps**:
   ```bash
   # Restart services
   systemctl --user restart roxy-core
   cd /opt/roxy/compose
   docker-compose -f docker-compose.foundation.yml restart
   ```

3. **Escalation**: Contact on-call engineer immediately

#### Security Breach

1. **Immediate Actions**:
   ```bash
   # Rotate all tokens
   /opt/roxy/scripts/rotate_token.sh
   
   # Check audit logs
   grep -i "BLOCKED\|AUTH\|SECURITY" ~/.roxy/logs/audit.log | tail -50
   
   # Check for unauthorized access
   grep -i "unauthorized\|forbidden" ~/.roxy/logs/roxy_core.log
   ```

2. **Containment**:
   - Disable affected services
   - Isolate compromised systems
   - Preserve logs for investigation

3. **Notification**: Notify security team immediately

### P1 - High Priority

#### Service Degradation

1. **Diagnosis**:
   ```bash
   # Check health
   /opt/roxy/scripts/health_check.sh
   
   # Check metrics
   curl http://localhost:9091/metrics | grep roxy_errors
   
   # Check resource usage
   docker stats
   ```

2. **Mitigation**:
   - Restart affected services
   - Scale resources if needed
   - Check for rate limiting issues

### P2 - Medium Priority

#### Performance Issues

1. **Investigation**:
   ```bash
   # Check Prometheus metrics
   curl http://localhost:9091/metrics | grep roxy_request_duration
   
   # Check logs for slow queries
   grep -i "slow\|timeout" ~/.roxy/logs/roxy_core.log
   ```

2. **Resolution**:
   - Optimize queries
   - Increase resource limits
   - Enable caching

## Communication

### Internal Communication

- **Slack/Teams**: #roxy-incidents channel
- **Email**: roxy-team@example.com
- **On-Call**: PagerDuty/OpsGenie

### External Communication

- **Status Page**: Update status page
- **Users**: Notify affected users
- **Stakeholders**: Regular updates

## Post-Incident

### Incident Report

1. **Timeline**: What happened when
2. **Root Cause**: Why it happened
3. **Impact**: Who/what was affected
4. **Resolution**: How it was fixed
5. **Prevention**: How to prevent recurrence

### Follow-Up Actions

- [ ] Update documentation
- [ ] Fix root cause
- [ ] Improve monitoring
- [ ] Update runbooks
- [ ] Conduct post-mortem

## Contact Information

- **On-Call Engineer**: [Contact]
- **Security Team**: [Contact]
- **Infrastructure Team**: [Contact]

## Related Documentation

- `docs/runbooks/TROUBLESHOOTING.md` - Troubleshooting guide
- `docs/DISASTER_RECOVERY.md` - Disaster recovery procedures
- `docs/INFRASTRUCTURE.md` - Infrastructure details

