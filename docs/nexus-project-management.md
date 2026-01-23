# NEXUS Project Management System

*Last Updated: 2026-01-21*
*Auto-managed by domain-specialized agents*

---

## 📋 Quick Reference
- **Philip's Required Tasks**: Section 1 - Only Philip can do these (API keys, purchases, etc.)
- **Expansion Queue**: Section 2 - Approved features ready for implementation
- **Project Planning**: Section 3 - Agent critiques & sharpening of upcoming ideas
- **Automation Status**: Section 4 - What's automated vs manual

---

## 1. 🔐 PHILIP'S REQUIRED TASKS
*Tasks only Philip can perform (API keys, purchases, registrations)*

### **High Priority** (Blocking Development)
| Task | Description | Why Only Philip | Status | Notes |
|------|-------------|-----------------|--------|-------|
| **Home Assistant Long-Lived Access Token** | Generate HA token for device control | Needs Philip's HA credentials | 🟡 Pending | Required for `home_assistant_action` tool |
| **Backup System Setup** | Create Backblaze account and configure backup credentials | Account creation and financial transaction | 🟡 Pending | Required for automated backups; BACKBLAZE_ACCOUNT_ID, BACKBLAZE_APP_KEY, RESTIC_PASSWORD in .env |
| **Security Review** | Review authentication for external access, implement API security | Security decisions require human approval | 🟡 Pending | Prevent unauthorized access if Nexus exposed to internet |
| **Additional AI API Keys** | Sign up for more AI provider free tiers | Account creation required | 🟢 Optional | Current providers (Groq, DeepSeek) are sufficient |
| **Purchase Hardware** | Buy any needed hardware (sensors, etc.) | Financial transaction | 🟢 Optional | No immediate hardware needs |

### **Medium Priority** (Enable New Features)
| Task | Description | Why Only Philip | Status | Notes |
|------|-------------|-----------------|--------|-------|
| **iPhone/Apple Watch Integration Setup** | Configure native app connections | Device-specific setup | 🟡 Pending | Can start with Home Assistant integration |
| **External Service Accounts** | Sign up for weather APIs, news APIs, etc. | Account creation | 🟢 Optional | Web search covers most needs |
| **Financial API Connections** | Connect banking/credit APIs | Sensitive financial data | 🔴 Blocked | Privacy/security concerns - use manual entry |

### **Low Priority** (Nice-to-Have)
| Task | Description | Why Only Philip | Status | Notes |
|------|-------------|-----------------|--------|-------|
| **Domain Registration** | Register nexus-ai.com or similar | Financial transaction | 🟢 Optional | Not required for development |
| **Cloud Service Accounts** | AWS/GCP/Azure for scaling | Financial/account setup | 🟢 Optional | Local development sufficient |

### **Automation Notes**
- **🔴 Blocked**: Cannot automate - requires Philip
- **🟡 Pending**: Philip action needed soon
- **🟢 Optional**: Can proceed without, but would enable features
- **✅ Complete**: Task done

---

## 2. 🚀 NEXUS EXPANSION QUEUE
*Approved features and ideas ready for implementation*

### **Priority 1: Now Implementing**
*Active development - agents working on these*

1. **✅ Enhanced Intelligent Chat**
   - **Status**: COMPLETED (2026-01-21)
   - **Domain Specialist**: AI/ML Integration Agent
   - **Description**: Digital god persona with full tool execution, web search, real-time context
   - **Components**: Tool detection, DuckDuckGo integration, enhanced prompts
   - **Next**: Test edge cases, optimize latency

2. **🔄 Finance Agent Creation**
   - **Status**: IN PROGRESS
   - **Domain Specialist**: Finance Tracking Agent
   - **Description**: Dedicated agent for budget monitoring, expense analysis, debt tracking
   - **Components**: Extend BaseAgent, integrate with finance database tables
   - **Blockers**: None

### **Priority 2: Next in Queue**
*Ready for agent assignment*

3. **iPhone Quick Expense Shortcut**
   - **Domain Specialist**: n8n Automation Agent + Finance Agent
   - **Description**: iOS Shortcut to quickly log expenses via voice/text
   - **Components**: n8n webhook, Shortcuts app integration, expense validation
   - **Dependencies**: Finance Agent completion

4. **Home Assistant Full Integration**
   - **Domain Specialist**: Home Automation Agent + AI/ML Agent
   - **Description**: Complete Home Assistant control (lights, devices, iPhone presence)
   - **Components**: HA API client, device discovery, action templates
   - **Blockers**: Philip's HA token (Section 1)

5. **Agent Framework UI**
   - **Domain Specialist**: General Purpose Agent + Architect
   - **Description**: Web interface to monitor/control agents
   - **Components**: FastAPI templates, real-time status, tool execution UI
   - **Dependencies**: Agent framework stabilization

### **Priority 3: Future Enhancements**
*Approved but lower priority*

6. **Semantic Memory Consolidation**
   - **Domain Specialist**: Memory Agent + AI/ML Agent
   - **Description**: Automated memory consolidation and knowledge extraction
   - **Components**: Memory analysis jobs, pattern detection, summary generation

7. **Multi-modal Input Processing**
   - **Domain Specialist**: AI/ML Agent + General Purpose Agent
   - **Description**: Process images, voice, documents alongside text
   - **Components**: Image analysis, speech-to-text, document parsing

8. **Predictive Analytics Engine**
   - **Domain Specialist**: Finance Agent + AI/ML Agent
   - **Description**: Predict expenses, budget breaches, financial trends
   - **Components**: Time series analysis, forecasting models, alert system

---

## 3. 🧠 PROJECT PLANNING & CRITIQUE
*Agent analysis of upcoming projects - sharpening ideas before implementation*

### **iPhone Quick Expense Shortcut - Agent Critique**

**Architect Agent Analysis:**
- **Technical Approach**: n8n webhook → FastAPI → database
- **Security Concerns**: Requires authentication for expense logging
- **Scalability**: Simple - single endpoint with validation
- **Integration Points**: iOS Shortcuts app, n8n, FastAPI finance router

**Finance Agent Analysis:**
- **Data Validation**: Must validate category, amount, date
- **User Experience**: Should confirm transaction immediately
- **Error Handling**: Handle invalid categories, duplicate entries
- **Follow-up**: Could trigger budget alerts if near limits

**Security Agent Analysis:**
- **Authentication**: API key or session token required
- **Rate Limiting**: Prevent spam expense logging
- **Data Privacy**: Expense data is sensitive - encrypt in transit
- **Recommendation**: Use existing session system with short-lived tokens

### **Home Assistant Full Integration - Agent Critique**

**Home Automation Agent Analysis:**
- **API Pattern**: Use official Home Assistant Python library
- **Device Discovery**: Automatically discover available entities
- **Action Templates**: Pre-configured actions for common scenarios
- **Error Recovery**: Handle device offline, network issues

**AI/ML Agent Analysis:**
- **Natural Language to HA Actions**: Parse "turn on living room lights" → HA service call
- **Context Awareness**: Consider time of day, presence detection
- **Learning Patterns**: Learn Philip's device usage patterns
- **Proactive Actions**: Suggest automations based on behavior

**Security Agent Analysis:**
- **Token Security**: Long-lived tokens must be encrypted at rest
- **Scope Limitation**: Token should have minimal necessary permissions
- **Audit Logging**: Log all HA actions with agent attribution
- **Network Security**: Local network only, no external exposure needed

### **Agent Framework UI - Agent Critique**

**Architect Agent Analysis:**
- **Technology Stack**: FastAPI + HTMX or React frontend
- **Real-time Updates**: WebSocket for agent status changes
- **Modular Design**: Separate components for agents, tools, sessions
- **Performance**: Should not impact agent performance

**General Purpose Agent Analysis:**
- **User Experience**: Clean, intuitive interface showing agent hierarchy
- **Debug Tools**: Real-time log viewing, tool execution testing
- **Mobile Responsive**: Should work on iPhone for monitoring
- **Export Features**: Export agent performance data

**Code Reviewer Analysis:**
- **Code Quality**: Type-safe Python, proper error handling
- **Testing Requirements**: Comprehensive UI tests
- **Documentation**: API docs + UI usage guide
- **Maintenance**: Easy to add new agent types/views

---

## 4. 🤖 AUTOMATION STATUS
*What's automated vs requires manual intervention*

### **Fully Automated** ✅
- **Agent Deployment**: New agents auto-registered via registry
- **Tool Execution**: Tools auto-discovered and validated
- **Web Search**: Real-time searches triggered by chat detection
- **Context Retrieval**: Multi-domain data retrieval on intelligent chat
- **API Testing**: Automated endpoint validation via test scripts

### **Partially Automated** 🔄
- **Project Planning**: This document structure - needs agent updates
- **Task Tracking**: Philip's tasks section needs manual status updates
- **Priority Queue**: Expansion queue requires manual re-prioritization

### **Manual Required** 🔴
- **Philip's Tasks**: Only Philip can complete these
- **Hardware Setup**: Physical device configuration
- **External Account Creation**: API key registration
- **Financial Transactions**: Any purchases

---

## 5. 📱 INTEGRATION ROADMAP
*Connecting to Philip's personal systems*

### **Immediate (Current)**
- **File-based**: This document in `~/nexus/nexus-project-management.md`
- **Terminal Access**: Philip can view/edit via terminal
- **Agent Reference**: All agents can read this file for context

### **Short-term (Next 2 Weeks)**
- **iPhone Reminders Integration**:
  - Sync Philip's tasks to iOS Reminders app
  - Due dates, priority flags, completion tracking
  - Bi-directional sync (complete in Reminders → update here)
- **Notes App Integration**:
  - Project planning sections to Apple Notes
  - Rich text formatting, checklists
  - Searchable across devices

### **Medium-term (Next Month)**
- **Native Desktop App**:
  - Linux desktop application for project management
  - Real-time agent status dashboard
  - Tool execution interface
  - Notification center
- **Premium Terminal Interface**:
  - Rich TUI (Text User Interface)
  - Color-coded status, progress bars
  - Keyboard shortcuts for common actions
  - Live agent monitoring

### **Long-term (Vision)**
- **All-in-One NEXUS Management Suite**:
  - Unified interface for all NEXUS capabilities
  - Drag-drop agent orchestration
  - Visual tool builder
  - Performance analytics dashboard
  - Cross-platform (Linux, iOS, Web)

---

## 6. 🎯 AGENT RESPONSIBILITIES
*Which agents manage which sections*

### **Primary Maintainers**
- **Section 1 (Philip's Tasks)**: General Purpose Agent + Philip manual updates
- **Section 2 (Expansion Queue)**: Architect Agent + Domain Specialists
- **Section 3 (Project Planning)**: All agents contribute critiques
- **Section 4 (Automation)**: Automation Agent + Code Reviewer
- **Section 5 (Integration)**: General Purpose Agent + Architect

### **Update Triggers**
- **Daily**: Check Philip's task status, update queue priorities
- **Weekly**: Agent critiques of next 2 queue items
- **On Completion**: Move completed items to "Recently Completed"
- **On Blocker**: Highlight blocked tasks in red, notify in daily summary

### **Quality Standards**
- **Clarity**: Each task must have clear success criteria
- **Actionable**: Tasks should be specific enough to implement
- **Prioritized**: Clear priority levels with justification
- **Ownership**: Each item has responsible agent(s)

---

## 7. 🛠 TECHNICAL DEBT & BUG FIXES
*Automated tasks that agents can handle - categorized by priority*

### **High Priority** (Critical Bugs)
*Blocking errors that need immediate attention*

1. **Fix Monitoring UUID Validation Error**
   - **Description**: Monitoring system uses 'system' as agent_id causing UUID validation errors
   - **Location**: `app/agents/monitoring.py` - metrics flushing
   - **Impact**: Spams logs every minute, breaks metrics collection
   - **Domain Specialist**: General Purpose Agent + Code Reviewer

2. **Implement Vector Similarity Search with pgvector**
   - **Description**: Complete cache service vector search implementation
   - **Location**: `app/services/cache_service.py:156`
   - **Impact**: Semantic caching incomplete, affects cost optimization
   - **Domain Specialist**: AI/ML Integration Agent + PostgreSQL DB Agent

3. **Integrate with Actual Notification System**
   - **Description**: Connect tools and monitoring to ntfy.sh
   - **Location**: `app/agents/tools.py:1111`, `app/agents/monitoring.py:979`
   - **Impact**: Notifications not functional
   - **Domain Specialist**: General Purpose Agent + Automation Agent

### **Medium Priority** (Feature Completion)
*Partially implemented features that need finishing*

1. **Complete Vector Memory System Integration**
   - **Location**: `app/agents/base.py:588,593,598`, `app/agents/memory.py`
   - **Components**: Triple extraction, summarization, clustering, knowledge graph
   - **Domain Specialist**: Memory Agent + AI/ML Agent

2. **Implement Agent Loading from Registry**
   - **Location**: `app/agents/base.py:806`
   - **Impact**: Agent persistence and restart capability
   - **Domain Specialist**: General Purpose Agent

3. **Complete MCP Integration in Nexus Master**
   - **Location**: `app/agents/nexus_master.py:1055,1082,1107`
   - **Components**: Database query, filesystem access, agent command execution
   - **Domain Specialist**: General Purpose Agent + Code Reviewer

### **Low Priority** (Enhancements)
*Improvements that can wait*

1. **Enhance Registry Agent Selection**
   - **Location**: `app/agents/registry.py:747,748`
   - **Components**: Semantic matching, workload consideration
   - **Domain Specialist**: Architect Agent

2. **Improve Monitoring Integration**
   - **Location**: `app/agents/monitoring.py:757,914`
   - **Components**: Orchestrator queue metrics, system-wide alerts
   - **Domain Specialist**: General Purpose Agent

### **Update Protocol**
- Agents should claim tasks from their domain
- Fixes should include tests to prevent regression
- Document changes in CLAUDE.md if architecture affected

---

*This document is living - agents should update their sections as work progresses. Philip should review Section 1 weekly and complete tasks as able.*