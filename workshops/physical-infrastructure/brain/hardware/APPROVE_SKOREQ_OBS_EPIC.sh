#!/bin/bash
# SKOREQ OBS Dream Collection - Epic Approval & Enqueue Script
# This script adds the SKOREQ-OBS-EPIC-001 to master-progress.json
# and enqueues the critical stories for execution.

set -e

MINDSONG_ROOT="/home/mark/mindsong-juke-hub"
MASTER_PROGRESS="$MINDSONG_ROOT/public/releaseplan/master-progress.json"
EPIC_TICKETS="/home/mark/.roxy/workshops/physical-infrastructure/brain/hardware/SKOREQ_OBS_EPIC_TICKETS.json"
LUNO_CLI="$MINDSONG_ROOT/luno-orchestrator/src/cli/luno.ts"

echo "═══════════════════════════════════════════════════════════════════"
echo "        SKOREQ OBS DREAM COLLECTION - GOVERNANCE APPROVAL          "
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Validate files exist
if [ ! -f "$MASTER_PROGRESS" ]; then
    echo "❌ ERROR: master-progress.json not found at: $MASTER_PROGRESS"
    exit 1
fi

if [ ! -f "$EPIC_TICKETS" ]; then
    echo "❌ ERROR: SKOREQ_OBS_EPIC_TICKETS.json not found at: $EPIC_TICKETS"
    exit 1
fi

echo "✓ Found master-progress.json"
echo "✓ Found SKOREQ_OBS_EPIC_TICKETS.json"
echo ""

# Check if epic already exists
if grep -q "SKOREQ-OBS-EPIC-001" "$MASTER_PROGRESS"; then
    echo "⚠️  SKOREQ-OBS-EPIC-001 already exists in master-progress.json"
    echo "   Skipping epic insertion (already registered)"
else
    echo "📝 Adding SKOREQ-OBS-EPIC-001 to master-progress.json..."
    
    # Create the epic JSON to insert using jq
    cd "$MINDSONG_ROOT"
    
    # Use node/bun to merge the epic into master-progress.json
    bun -e "
const fs = require('fs');
const masterPath = '$MASTER_PROGRESS';
const ticketsPath = '$EPIC_TICKETS';

const master = JSON.parse(fs.readFileSync(masterPath, 'utf-8'));
const tickets = JSON.parse(fs.readFileSync(ticketsPath, 'utf-8'));

// Convert ticket format to master-progress format
const newEpic = {
  id: tickets.epic.id,
  name: tickets.epic.title,
  category: 'infrastructure',
  description: tickets.epic.description,
  status: 'in_progress',
  percent: 0,
  priority: 'critical',
  focusEpic: true,
  phases: [],
  sprints: [
    {
      id: 'SKOREQ-OBS-EPIC-001-S1',
      name: 'Foundation Sprint',
      description: 'NDI Bridge, AI Plugins, ROXY Integration',
      status: 'todo',
      startDate: '2026-01-09',
      stories: tickets.stories.filter(s => ['STORY-001', 'STORY-002', 'STORY-003'].some(x => s.id.includes(x))).map(s => ({
        id: s.id,
        title: s.title,
        description: s.description,
        status: 'todo',
        type: 'task',
        priority: s.priority,
        sprintId: 'SKOREQ-OBS-EPIC-001-S1',
        storyPoints: s.storyPoints,
        epicId: tickets.epic.id,
        lunoPrefix: 'SKOREQ',
        tasks: [],
        filesInScope: s.filesInScope,
        acceptanceCriteria: s.acceptanceCriteria,
        dependencies: s.dependencies || [],
        points: s.storyPoints,
        swarmReady: true,
        executionProfile: 'SWARM',
        aiAssists: {
          skillsAllowed: ['luno-orchestrator-bible'],
          skillPurpose: 'Execute story per acceptance criteria; obey filesInScope.',
          skillScope: s.filesInScope
        }
      })),
      percent: 0
    },
    {
      id: 'SKOREQ-OBS-EPIC-001-S2',
      name: 'Architecture Sprint',
      description: 'Scene Collection, Masters, Verticals',
      status: 'todo',
      startDate: '2026-01-12',
      stories: tickets.stories.filter(s => ['STORY-004', 'STORY-005', 'STORY-006'].some(x => s.id.includes(x))).map(s => ({
        id: s.id,
        title: s.title,
        description: s.description,
        status: 'todo',
        type: 'task',
        priority: s.priority,
        sprintId: 'SKOREQ-OBS-EPIC-001-S2',
        storyPoints: s.storyPoints,
        epicId: tickets.epic.id,
        lunoPrefix: 'SKOREQ',
        tasks: [],
        filesInScope: s.filesInScope,
        acceptanceCriteria: s.acceptanceCriteria,
        dependencies: s.dependencies || [],
        points: s.storyPoints,
        swarmReady: true,
        executionProfile: 'SWARM',
        aiAssists: {
          skillsAllowed: ['luno-orchestrator-bible'],
          skillPurpose: 'Execute story per acceptance criteria; obey filesInScope.',
          skillScope: s.filesInScope
        }
      })),
      percent: 0
    },
    {
      id: 'SKOREQ-OBS-EPIC-001-S3',
      name: 'Polish Sprint',
      description: 'Overlays, Animations, MIDI, Documentation',
      status: 'todo',
      startDate: '2026-01-16',
      stories: tickets.stories.filter(s => ['STORY-007', 'STORY-008', 'STORY-009', 'STORY-010'].some(x => s.id.includes(x))).map(s => ({
        id: s.id,
        title: s.title,
        description: s.description,
        status: 'todo',
        type: 'task',
        priority: s.priority,
        sprintId: 'SKOREQ-OBS-EPIC-001-S3',
        storyPoints: s.storyPoints,
        epicId: tickets.epic.id,
        lunoPrefix: 'SKOREQ',
        tasks: [],
        filesInScope: s.filesInScope,
        acceptanceCriteria: s.acceptanceCriteria,
        dependencies: s.dependencies || [],
        points: s.storyPoints,
        swarmReady: true,
        executionProfile: 'SWARM',
        aiAssists: {
          skillsAllowed: ['luno-orchestrator-bible'],
          skillPurpose: 'Execute story per acceptance criteria; obey filesInScope.',
          skillScope: s.filesInScope
        }
      })),
      percent: 0
    }
  ]
};

// Add the new epic
master.epics.push(newEpic);

// Write back
fs.writeFileSync(masterPath, JSON.stringify(master, null, 2));
console.log('✅ SKOREQ-OBS-EPIC-001 added to master-progress.json');
console.log('   - 3 sprints');
console.log('   - 10 stories');
console.log('   - 44 story points total');
"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    ENQUEUE CRITICAL STORIES                        "
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Enqueue the critical stories (parallel-safe - no dependencies between them)
echo "📤 Enqueueing STORY-001 (NDI Widget Bridge) to free-tier..."
cd "$MINDSONG_ROOT/luno-orchestrator"
bun run src/cli/luno.ts enqueue --story=SKOREQ-OBS-EPIC-001-STORY-001 --queue=free-tier

echo ""
echo "📤 Enqueueing STORY-002 (AI Plugin Configuration) to free-tier..."
bun run src/cli/luno.ts enqueue --story=SKOREQ-OBS-EPIC-001-STORY-002 --queue=free-tier

echo ""
echo "📤 Enqueueing STORY-003 (ROXY MCP Integration) to free-tier..."
bun run src/cli/luno.ts enqueue --story=SKOREQ-OBS-EPIC-001-STORY-003 --queue=free-tier

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                         GOVERNANCE STATUS                          "
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "✅ SKOREQ-OBS-EPIC-001 registered in master-progress.json"
echo "✅ Sprint 1 stories (001, 002, 003) enqueued to free-tier"
echo ""
echo "📊 Remaining stories to enqueue after Sprint 1 completes:"
echo "   - STORY-004 (Scene Architecture) → paid-tier (8 points)"
echo "   - STORY-005 (Horizontal Masters) → free-tier"
echo "   - STORY-006 (Vertical Scenes) → free-tier"
echo "   - STORY-007 (Overlays) → free-tier"
echo "   - STORY-008 (Animations) → free-tier"
echo "   - STORY-009 (MIDI Integration) → free-tier"
echo "   - STORY-010 (Documentation) → free-tier"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Run 'luno status' to monitor execution progress"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
