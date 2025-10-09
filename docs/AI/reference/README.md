# AI Reference Documentation

**Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Comprehensive reference documentation for AI agents and development team

---

## 📚 Documentation Index

This directory contains detailed reference documentation for the Data Warehouse project. These documents are designed to be used by:
- **AI Agents** (PM, Architect, Developer, Tester, Documenter)
- **Human Developers** joining the project
- **Product Managers** creating requirements
- **Architects** making technical decisions

---

## 🗂️ Available Documents

### 1. [ARCHITECTURE.md](ARCHITECTURE.md)
**System Architecture Overview**

- Complete system architecture and design patterns
- Layer-by-layer breakdown (Presentation → Service → Sync Engine → Client → Processor → Model)
- CRM Integration Framework
- Component relationships and data flow
- Technology stack
- Design patterns in use (Template Method, Strategy, Repository, etc.)

**When to use**: Understanding system structure, adding new integrations, architectural decisions

---

### 2. [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
**Database Schema Reference**

- All database models across 11+ CRMs
- Table definitions with field descriptions
- Relationships between models
- Indexes and performance considerations
- Migration strategies
- Database conventions

**When to use**: Creating new models, understanding data structure, writing queries, debugging data issues

---

### 3. [API_INTEGRATIONS.md](API_INTEGRATIONS.md)
**API & Integration Reference**

- Complete API documentation for all CRM integrations
- Endpoint details and authentication methods
- Sync engine implementations
- Client and processor patterns
- Rate limits and pagination
- Example usage code

**When to use**: Adding CRM integrations, fixing sync issues, understanding API patterns

---

### 4. [EXISTING_TESTS.md](EXISTING_TESTS.md)
**Existing Tests Documentation** ⭐ User Priority

- Catalog of all 183+ test files
- Test categories (Unit, Integration, E2E)
- Test infrastructure and base classes
- Safety levels and data control
- Running tests guide
- Test coverage by CRM

**When to use**: Writing new tests, understanding test patterns, running test suites, debugging test failures

---

### 5. [PM_GUIDE.md](PM_GUIDE.md)
**PM Reference Guide**

- Requirements templates
- User story format (As a... I want... So that...)
- Acceptance criteria patterns
- CRM integration requirements template
- Dashboard feature requirements
- Bug report and feature request templates
- Working with AI agents

**When to use**: Creating requirements, writing user stories, defining acceptance criteria, feature planning

---

### 6. [CODEBASE_MAP.md](CODEBASE_MAP.md)
**Codebase Navigation Map**

- Directory structure breakdown
- Quick find guide ("I need to...")
- Component location reference
- URL patterns
- Configuration files
- Common file patterns
- Search strategies

**When to use**: Finding components, navigating codebase, locating functionality, understanding project structure

---

## 🚀 Quick Start Guide

### For AI Agents

1. **Starting New Work**:
   - Read [PM_GUIDE.md](PM_GUIDE.md) to understand requirements format
   - Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design patterns
   - Use [CODEBASE_MAP.md](CODEBASE_MAP.md) to find relevant files

2. **Adding CRM Integration**:
   - Follow template in [PM_GUIDE.md](PM_GUIDE.md) → "CRM Integration Requirements"
   - Reference [ARCHITECTURE.md](ARCHITECTURE.md) → "CRM Integration Framework"
   - Use [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for model patterns
   - Check [API_INTEGRATIONS.md](API_INTEGRATIONS.md) for similar integrations

3. **Fixing Bugs**:
   - Use [CODEBASE_MAP.md](CODEBASE_MAP.md) to locate affected files
   - Check [EXISTING_TESTS.md](EXISTING_TESTS.md) for relevant tests
   - Reference [ARCHITECTURE.md](ARCHITECTURE.md) for expected behavior

4. **Writing Tests**:
   - Read [EXISTING_TESTS.md](EXISTING_TESTS.md) thoroughly
   - Follow existing test patterns
   - Use test infrastructure (CRMCommandTestBase, mixins)

### For Human Developers

1. **Onboarding**:
   ```
   Day 1: Read ARCHITECTURE.md + CODEBASE_MAP.md
   Day 2: Read DATABASE_SCHEMA.md + API_INTEGRATIONS.md
   Day 3: Read EXISTING_TESTS.md, run some tests
   Day 4: Start contributing with PM_GUIDE.md as reference
   ```

2. **Daily Development**:
   - Keep [CODEBASE_MAP.md](CODEBASE_MAP.md) open for quick navigation
   - Reference [API_INTEGRATIONS.md](API_INTEGRATIONS.md) when working with CRM APIs
   - Check [EXISTING_TESTS.md](EXISTING_TESTS.md) before writing new tests

### For Product Managers

1. **Creating Requirements**:
   - Use templates in [PM_GUIDE.md](PM_GUIDE.md)
   - Reference [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for data model
   - Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical feasibility

2. **Feature Planning**:
   - Review [API_INTEGRATIONS.md](API_INTEGRATIONS.md) for integration scope
   - Use [EXISTING_TESTS.md](EXISTING_TESTS.md) to understand testing needs

---

## 📊 Documentation Coverage

| Area | Document | Completeness |
|------|----------|--------------|
| System Architecture | ARCHITECTURE.md | ✅ 100% |
| Database Schema | DATABASE_SCHEMA.md | ✅ 100% |
| API Integrations | API_INTEGRATIONS.md | ✅ 100% |
| Test Documentation | EXISTING_TESTS.md | ✅ 100% |
| PM Guidelines | PM_GUIDE.md | ✅ 100% |
| Code Navigation | CODEBASE_MAP.md | ✅ 100% |

---

## 🔄 Documentation Maintenance

### When to Update

- **After adding new CRM**: Update all relevant documents
- **After architectural changes**: Update ARCHITECTURE.md
- **After adding models**: Update DATABASE_SCHEMA.md
- **After writing tests**: Update EXISTING_TESTS.md
- **Quarterly reviews**: All documents

### Update Checklist

When adding a new CRM integration:
- [ ] Update DATABASE_SCHEMA.md with new models
- [ ] Update API_INTEGRATIONS.md with endpoints and engines
- [ ] Update ARCHITECTURE.md if new patterns introduced
- [ ] Update EXISTING_TESTS.md with new test files
- [ ] Update CODEBASE_MAP.md with new file locations
- [ ] Update PM_GUIDE.md if new requirement patterns emerge

---

## 🤝 Contributing to Documentation

### Documentation Standards

1. **Clarity**: Write for both AI and human readers
2. **Examples**: Include code examples
3. **Completeness**: Cover all aspects
4. **Accuracy**: Verify against actual code
5. **Consistency**: Follow existing formats

### Pull Request Checklist

- [ ] Documentation matches actual implementation
- [ ] All code examples tested
- [ ] Cross-references updated
- [ ] Formatting consistent
- [ ] No typos or grammar errors

---

## 📞 Support

- **GitHub Issues**: File issues for documentation improvements
- **Pull Requests**: Submit updates directly
- **Team Chat**: Discuss clarifications
- **Code Comments**: Always document complex logic

---

## 🎯 Best Practices

### For AI Agents

1. **Always reference documentation** before starting work
2. **Follow existing patterns** documented in ARCHITECTURE.md
3. **Use templates** from PM_GUIDE.md
4. **Check EXISTING_TESTS.md** before writing tests
5. **Update documentation** after completing work

### For Developers

1. **Read documentation first** before asking questions
2. **Use CODEBASE_MAP.md** to navigate efficiently
3. **Reference API_INTEGRATIONS.md** for integration work
4. **Keep documentation up to date** with code changes

### For Product Managers

1. **Use PM_GUIDE.md templates** for all requirements
2. **Include acceptance criteria** following documented patterns
3. **Reference technical docs** when assessing feasibility
4. **Work with architects** on complex features

---

## 📈 Related Resources

### External Documentation
- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Project Documentation
- [Main README](../../../README.md)
- [CRM Sync Guide](../../crm_sync_guide.md)
- [Current CRM Implementation](../../current_crm_implementation.md)
- [CRM Dashboard Requirements](../../CRM_DASHBOARD_REQUIREMENTS.md)

### Google ADK Documentation
- [Setup Guide](../SETUP_GUIDE.md)
- [Quick Reference](../QUICK_REFERENCE.md)
- [Integration Summary](../INTEGRATION_SUMMARY.md)

---

**Documentation Maintained By**: Development Team & AI Agents  
**Last Review**: 2025  
**Next Review**: Quarterly  
**Questions**: Contact development team or file GitHub issue
