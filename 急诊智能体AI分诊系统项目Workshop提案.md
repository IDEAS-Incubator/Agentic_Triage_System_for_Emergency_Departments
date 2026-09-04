**题目：**

**两次 Workshop，带你从零拆解一个真正的 Healthcare Agentic AI 项目**

**副标题：**

**Healthcare + Agentic AI + Multi-Agent + RAG + HL7/FHIR + AI Safety/Compliance**

**内容：**

**当 Agentic AI 遇上 Healthcare：我们到底应该怎样设计一个可以真正落地的 AI 系统？**

2026 年，AI 的竞争正在从"会不会调用大模型"，快速进入到，**能不能把 LLM、Agent、RAG、企业数据、安全合规和真实业务流程整合成一个完整的 AI System。**Healthcare 正是最值得研究、同时也是最具挑战性的 AI 应用领域之一。医疗系统拥有大量患者历史、检验结果、药物记录、临床指南等数据，但这些信息往往分散在不同系统中。特别是在 Emergency Department（ED，急诊科），医护人员需要在很短时间内，根据患者主诉、生命体征和有限信息完成 Triage（分诊）。

那么，一个非常有意思的问题来了,**我们能不能利用 Agentic AI + RAG + Healthcare Data，构建一个 AI Triage Assistant，帮助医护人员更快地找到重要信息、识别风险，并给出有证据支持的分诊建议？**围绕这个问题，我们设计了一个完整的项目， **Agentic AI Triage System for Emergency Departments**

这是一个结合：

**LLM + Multi-Agent + RAG + HL7/FHIR + Clinical Data + Explainable AI + AI Safety**

的 Healthcare AI 项目。

为了让大家真正理解一个 Healthcare Agentic AI System 是如何从 Idea 走向 Architecture 和 Implementation 的，我们将通过 **两次 Workshop**，带大家完整拆解这个项目。

**Workshop - 1**

**从 Healthcare Problem 到 Agentic AI System Architecture**

第一次 Workshop，我们重点解决一个问题：

**一个真实的 Healthcare AI 项目，应该怎样做 System Design？**

我们不会从 Prompt 开始，而是从真正的 Healthcare Workflow 开始。

你将了解到急诊患者进入医院以后，数据是怎样产生和流动的，包括：

- HL7 ADT：患者 Admission / Discharge / Transfer
- HL7 ORM：医疗 Order
- HL7 ORU：Lab、Imaging、Vitals 等结果
- FHIR Patient / Encounter / Observation / Condition
- MedicationRequest
- DiagnosticReport

然后我们会进一步讨论,**怎样把这些传统 Healthcare Data Infrastructure 与现代 LLM 连接起来？**

整个系统将被拆成四层：

**Healthcare Data Integration → Private RAG → Agent Orchestration → Clinician Interface**

我们会重点讲解为什么 Healthcare AI 不能简单地把所有患者信息直接塞进 Prompt，而应该建立 Structured Patient Context + RAG Retrieval 的架构。

**Workshop - 2**

**Multi-Agent、RAG、Guardrails 与 Healthcare AI Safety**

第二次 Workshop，我们进入整个项目最核心的部分, **Agentic AI Workflow**

在这个系统里，我们不会使用一个巨大的 Prompt 让一个 LLM 完成所有工作，而是把任务拆成多个 Specialized Agents。 你将看到一个完整的 Multi-Agent Workflow：

**① Intake Agent**

负责接收和标准化 HL7 / FHIR 数据，建立患者当前就诊的基本 Context。

**② History & Retrieval Agent**

从患者历史记录中寻找：

- Chronic conditions
- Medication history
- Allergies
- Previous ED visits
- Abnormal lab results

同时通过 RAG 检索相关的医疗指南和 Triage Criteria。

**③ Risk-Rules Agent**

在 LLM 推理之前，首先执行确定性的 Risk Rules，例如：

- Vital-sign thresholds
- Sepsis screening
- Anticoagulant + head injury
- High-risk clinical red flags

也就是说,**不是所有事情都交给 LLM。**

在高风险 AI 系统中，Rule-based Guardrails 仍然非常重要。

**④ Triage Reasoning Agent**

LLM 综合：

**Chief Complaint + Vitals + Patient History + Retrieved Guidelines + Risk Rules**

生成建议的 CTAS / ESI Triage Level，并给出 Structured Rationale。

**⑤ Critic / Verification Agent**

这是整个系统非常关键的 Agent。

它负责检查：

**LLM 说的每一个重要事实，是否真的存在于 Retrieved Evidence 中？**

如果引用不存在、证据不足，或者违反 Risk Rule，系统就不能简单接受这个答案。

**⑥ Presentation & Audit Agent**

最后把 AI Recommendation、Evidence、Confidence 和 Explanation 组织成医护人员能够快速阅读的结果，同时记录完整 Audit Trail。

**为什么这个项目值得学习？**

很多 LLM Tutorial 教你的可能是,**Prompt → LLM → Answer**. 但是企业真正需要的 AI Engineer，需要思考的是**Data → Retrieval → Agent → Tools → Reasoning → Verification → Guardrails → Human → Audit**. 这也是这个 Workshop 最希望带给大家的能力。 你学习的不只是"Healthcare AI"，而是一套可以迁移到很多行业的 **Enterprise Agentic AI Architecture**。例如：

- Healthcare
- Finance
- Insurance
- Cybersecurity
- Legal AI
- Enterprise Knowledge Assistant
- Compliance AI

这些领域都有一个共同特点,**AI 不能只是给答案，还必须知道答案来自哪里、为什么可信，以及什么时候应该让人来做最终决定。**

**Healthcare AI 为什么特别适合 RAG？**

Healthcare 是学习 RAG 非常好的案例。因为一个患者可能同时拥有**Vitals + Labs + Medications + Conditions + Previous Encounters + Imaging + Clinical Notes + Guidelines**

真正的问题不是"LLM 知不知道医学知识"，而是**怎样在正确的时间，把正确患者的正确信息检索出来，并提供给正确的 Agent？**因此 Workshop 中我们会讨论：

**Structured Retrieval + Vector Search + Hybrid Retrieval + Metadata Filtering + Patient-level Access Control**

以及为什么 Healthcare RAG 的设计和普通"PDF Chatbot"完全不同。

**我们也会讨论一个非常重要的问题**

**Healthcare 到底应该用 GPT/Claude/Gemini，还是训练自己的 Healthcare LLM？**

我们会比较三种路线：

**Frontier LLM + RAG**

vs.

**Self-hosted Open-Weight LLM + RAG**

vs.

**Fine-tuned Healthcare Model**

并讨论什么时候应该使用 Frontier Model，什么时候因为 PHI、Data Residency、Latency、Cost 等原因需要考虑 Self-hosted Model，以及什么时候 Fine-tuning 才真正有意义。

**AI Engineer 必须懂的另一件事：Safety & Compliance**

Healthcare AI 和普通 Chatbot 最大的区别之一，就是：

**你不能只考虑 Accuracy。**

我们还必须考虑：

- Hallucination
- PHI Protection
- HIPAA / PHIPA
- Access Control
- Encryption
- Auditability
- Human-in-the-loop
- Automation Bias
- Model Verification
- Under-triage Risk

因此这个项目也是一个非常好的 **Responsible AI / AI Safety Engineering** 案例。

**谁适合参加这两次 Workshop？**如果你是：

**Software Engineer / Data Engineer / Data Scientist / ML Engineer / LLM Engineer / AI Engineer**

或者你正在学习：

**Prompt Engineering、RAG、Agent、Multi-Agent、LLM Application Development**

这两次 Workshop 都非常适合你。

尤其如果你已经学过一些 LLM 基础，却仍然不知道：

"真正公司的 Agentic AI 项目到底是怎么设计的？"

那么这个项目会是一个非常好的 End-to-End Case Study。

**两次 Workshop，你最终要带走什么？**

我们的目标不是让大家听完以后只记住几个 AI 名词。

而是希望大家能够真正理解：

**如何从一个真实 Business Problem 出发，设计一个完整的 Agentic AI System。**

从：

**Healthcare Workflow**

到

**HL7 / FHIR Data Integration**

到

**RAG**

到

**Multi-Agent Architecture**

到

**LLM Reasoning**

到

**Verification Agent**

到

**Guardrails**

再到

**Human-in-the-loop + Security + Compliance + Evaluation**

这才是一个完整的 AI Engineering Project。

**🚀 两次 Workshop，一起挑战一个真正的 Agentic AI 项目**

LLM 的时代正在快速进入 **Agentic AI** 阶段。

未来企业需要的，不只是会写 Prompt 的人，而是能够把：

**LLM + Agent + RAG + Data + Software Engineering + Domain Knowledge**

真正组合成一个可靠系统的 **AI Engineer**。

Healthcare Agentic AI 正是一个非常好的练兵场。

如果你想深入理解：

**Multi-Agent 到底怎么设计？**  
**RAG 在真实企业系统中到底怎么用？**  
**Healthcare Data 怎么接入 LLM？**  
**怎样减少 Hallucination？**  
**怎样设计 Verification Agent？**  
**怎样实现 Human-in-the-loop？**  
**怎样把一个 AI Demo 逐步变成 Enterprise AI System？**

欢迎参加我们的：

**《Agentic AI Triage System for Healthcare》两次实战 Workshop**

**我们不只是学习如何调用 LLM。**

**我们一起学习如何设计真正的 AI System。**

期待在 Workshop 和大家一起，从 Architecture 到 Agent Workflow，完整拆解这个 Healthcare Agentic AI 项目！