#!/usr/bin/env python3
"""
Orchestrator Agent - Cerebro del sistema agentic
Coordina todos los agentes especializados y GSD framework
"""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic
import subprocess


class Orchestrator:
    """
    Agente maestro que coordina el flujo completo:
    1. Recibe user input
    2. Crea user story
    3. Routing inteligente (decide qué agentes spawneará)
    4. Spawns specialized agents (Research, Architect, Documenter)
    5. Ejecuta GSD framework
    6. Monitorea CI/CD
    """
    
    def __init__(self, github_token: str, anthropic_api_key: str):
        self.client = AsyncAnthropic(api_key=anthropic_api_key)
        self.github_token = github_token
        self.github_api = "https://api.github.com"
        
        # Cargar system prompts
        prompts_dir = Path(__file__).parent / "prompts"
        self.prompts = {}
        
        for prompt_file in prompts_dir.glob("*.txt"):
            agent_name = prompt_file.stem
            self.prompts[agent_name] = prompt_file.read_text()
    
    async def handle_request(self, user_input: str, repo: str) -> str:
        """
        Punto de entrada principal
        
        Args:
            user_input: Descripción de la feature/tarea del usuario
            repo: Repositorio donde trabajar (formato: org/repo)
        
        Returns:
            URL del PR creado
        """
        
        print(f"\n{'='*60}")
        print(f"[BOT] ORCHESTRATOR: Processing request")
        print(f"{'='*60}\n")
        
        # 1. Crear user story
        print("[1] Step 1: Creating user story...")
        user_story = await self._create_user_story(user_input)
        print(f"[OK] User story created:\n{user_story['summary']}\n")
        
        # 2. Intelligent routing
        print("[2] Step 2: Intelligent routing...")
        agents_needed = self._decide_agents(user_story)
        print(f"[OK] Agents to spawn: {', '.join(agents_needed)}\n")
        
        # 3. Crear branch en GitHub
        print("[3] Step 3: Creating GitHub branch...")
        branch_name = f"feature/{self._slugify(user_story['title'])}"
        await self._create_branch(repo, branch_name)
        print(f"[OK] Branch created: {branch_name}\n")
        
        # 4. Spawn specialized agents (SEQUENTIAL por defecto)
        print("[4] Step 4: Spawning specialized agents...")
        specialist_results = await self._spawn_specialists_sequential(
            user_story, 
            agents_needed
        )
        print(f"[OK] Specialists completed\n")
        
        # 5. Ejecutar GSD
        print("[5] Step 5: Executing GSD framework...")
        await self._execute_gsd(
            user_story=user_story,
            context=specialist_results,
            repo=repo,
            branch=branch_name
        )
        print(f"[OK] GSD execution completed\n")
        
        # 6. Esperar CI/CD y PR
        print("[6] Step 6: Waiting for CI/CD and PR creation...")
        pr_url = await self._wait_for_pr(repo, branch_name)
        
        print(f"\n{'='*60}")
        print(f"[OK] ORCHESTRATOR: Request completed!")
        print(f"PR URL: {pr_url}")
        print(f"{'='*60}\n")
        
        return pr_url
    
    async def _create_user_story(self, user_input: str) -> Dict:
        """Genera user story estructurada a partir del input"""
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4000,
            system="""Eres un Product Manager experto.
Tu trabajo es convertir requests de usuarios en user stories estructuradas.

Formato de output (JSON):
{
    "title": "Título corto de la feature",
    "summary": "Como [rol], quiero [acción], para [beneficio]",
    "acceptance_criteria": ["Criterio 1", "Criterio 2", ...],
    "technical_notes": "Notas técnicas relevantes",
    "estimated_complexity": "low|medium|high"
}
""",
            messages=[{
                "role": "user",
                "content": f"Crea user story para: {user_input}"
            }]
        )
        
        # Parse JSON response
        content = response.content[0].text
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
    
    def _decide_agents(self, user_story: Dict) -> List[str]:
        """
        Intelligent routing: decide qué agentes se necesitan
        """
        
        agents = []
        
        story_text = json.dumps(user_story).lower()
        
        # Reglas de routing
        # SIEMPRE incluye researcher para nuevas features
        if any(word in story_text for word in [
            'añade', 'implementa', 'crea', 'nueva', 'añadir', 'agregar',
            'auth', 'integra', 'conecta'
        ]):
            agents.append('researcher')
        
        # Architect casi siempre necesario
        agents.append('architect')
        
        # Documenter siempre
        agents.append('documenter')
        
        # Security para auth/datos sensibles
        if any(word in story_text for word in [
            'auth', 'security', 'password', 'token', 'pharma', 'patient', 'hipaa'
        ]):
            agents.append('security')
        
        return list(set(agents))  # Remove duplicates
    
    async def _spawn_specialists_sequential(
        self, 
        user_story: Dict, 
        agents: List[str]
    ) -> Dict:
        """
        Spawns specialists en SECUENCIAL (estrategia MVP)
        Research → Architect → Documenter
        """
        
        results = {}
        
        # 1. Researcher (si necesario)
        if 'researcher' in agents:
            print("  [RESEARCH] Running Researcher Agent...")
            results['researcher'] = await self._spawn_researcher(user_story)
            print("  [OK] Researcher completed")
        
        # 2. Security (en paralelo con Researcher si ambos están)
        if 'security' in agents:
            print("  [SECURITY] Running Security Agent...")
            results['security'] = await self._spawn_security(user_story)
            print("  [OK] Security completed")
        
        # 3. Architect (usa research)
        if 'architect' in agents:
            print("  [ARCHITECT] Running Architect Agent...")
            results['architect'] = await self._spawn_architect(
                user_story,
                research=results.get('researcher'),
                security=results.get('security')
            )
            print("  [OK] Architect completed")
        
        # 4. Documenter (puede ir en paralelo, pero por simplicidad va después)
        if 'documenter' in agents:
            print("  [DOC] Running Documenter Agent...")
            results['documenter'] = await self._spawn_documenter(user_story)
            print("  [OK] Documenter completed")
        
        return results
    
    async def _spawn_researcher(self, user_story: Dict) -> str:
        """Spawns Research Agent"""
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            system=self.prompts['researcher'],
            messages=[{
                "role": "user",
                "content": f"""Research for this feature:

User Story:
{json.dumps(user_story, indent=2)}

Focus on:
- Best libraries/frameworks for this use case
- Best practices and patterns
- Security considerations
- Compliance requirements (pharma: 21 CFR Part 11, HIPAA, GDPR)
"""
            }],
            tools=[
                {"type": "web_search_20250305", "name": "web_search"}
            ]
        )
        
        # Extract text content
        return '\n'.join([
            block.text for block in response.content 
            if hasattr(block, 'text')
        ])
    
    async def _spawn_architect(
        self, 
        user_story: Dict,
        research: Optional[str] = None,
        security: Optional[str] = None
    ) -> str:
        """Spawns Architect Agent"""
        
        context_parts = [
            f"User Story:\n{json.dumps(user_story, indent=2)}"
        ]
        
        if research:
            context_parts.append(f"\nResearch Findings:\n{research}")
        
        if security:
            context_parts.append(f"\nSecurity Requirements:\n{security}")
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=16000,
            system=self.prompts['architect'],
            messages=[{
                "role": "user",
                "content": '\n\n'.join(context_parts)
            }]
        )
        
        return '\n'.join([
            block.text for block in response.content 
            if hasattr(block, 'text')
        ])
    
    async def _spawn_security(self, user_story: Dict) -> str:
        """Spawns Security Agent"""
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            system=self.prompts.get('security', 'You are a security expert.'),
            messages=[{
                "role": "user",
                "content": f"""Analyze security requirements for:

{json.dumps(user_story, indent=2)}

Focus on:
- Data protection (encryption, access control)
- Compliance (HIPAA, GDPR, 21 CFR Part 11)
- Audit logging requirements
- Security testing requirements
"""
            }]
        )
        
        return '\n'.join([
            block.text for block in response.content 
            if hasattr(block, 'text')
        ])
    
    async def _spawn_documenter(self, user_story: Dict) -> str:
        """Spawns Documenter Agent"""
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8000,
            system=self.prompts['documenter'],
            messages=[{
                "role": "user",
                "content": f"Create documentation for:\n{json.dumps(user_story, indent=2)}"
            }]
        )
        
        return '\n'.join([
            block.text for block in response.content 
            if hasattr(block, 'text')
        ])
    
    async def _create_branch(self, repo: str, branch_name: str):
        """Crea branch en GitHub"""
        
        import requests
        
        # Get default branch SHA
        url = f"{self.github_api}/repos/{repo}/git/refs/heads/main"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        sha = response.json()['object']['sha']
        
        # Create new branch
        create_url = f"{self.github_api}/repos/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        requests.post(create_url, headers=headers, json=payload)
    
    async def _execute_gsd(
        self,
        user_story: Dict,
        context: Dict,
        repo: str,
        branch: str
    ):
        """Ejecuta GSD framework"""
        
        # Crear archivo de contexto
        import tempfile
        context_file = Path(tempfile.gettempdir()) / 'gsd_context.json'
        context_file.write_text(json.dumps({
            'user_story': user_story,
            'research': context.get('researcher'),
            'architecture': context.get('architect'),
            'documentation': context.get('documenter'),
            'security': context.get('security')
        }, indent=2), encoding='utf-8')
        
        # Ejecutar GSD (esto es un placeholder, ajusta según tu setup)
        # En la práctica, GSD se ejecutaría con Claude Code
        print("  [5] GSD would execute here with context from specialists")
        print(f"  Context saved to: {context_file}")
    
    async def _wait_for_pr(self, repo: str, branch: str) -> str:
        """Espera a que se cree el PR (simplificado)"""
        
        # En la práctica, esto esperaría a que GitHub Actions cree el PR
        # Por ahora retornamos un placeholder
        return f"https://github.com/{repo}/pull/XXX"
    
    def _slugify(self, text: str) -> str:
        """Convierte texto a slug para nombres de branch"""
        
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')


async def main():
    """Entry point para testing"""
    
    github_token = os.getenv('GITHUB_TOKEN')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not github_token or not anthropic_key:
        print("Error: Set GITHUB_TOKEN and ANTHROPIC_API_KEY environment variables")
        sys.exit(1)
    
    orchestrator = Orchestrator(github_token, anthropic_key)
    
    # Test
    pr_url = await orchestrator.handle_request(
        user_input="Añade autenticación OAuth2 a la API",
        repo="your-org/your-repo"
    )
    
    print(f"PR created: {pr_url}")


if __name__ == "__main__":
    asyncio.run(main())
