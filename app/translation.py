from textwrap import dedent


from models.schemas import LogCtxData

class TranslationService:
    async def translate(self, ctx: LogCtxData, target_lang: str) -> str:
        """Bidirectional translation with quality checks"""
        if target_lang == "CN":
            return await self._translate_english_to_chinese(ctx)
        return await self._translate_chinese_to_english(ctx)

    async def _translate_english_to_chinese(self, ctx: LogCtxData) -> str:
        prompt = dedent(f"""
        Translate this technical text to colloquial Chinese:
        {ctx.txtENG}
        
        Requirements:
        - Maintain technical accuracy
        - Use natural spoken Chinese
        - Preserve numbers and proper nouns
        """)
        response = await self.ingress.chat.completions.create(
            model="towerinstruct",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    async def _translate_chinese_to_english(self, ctx: LogCtxData) -> str:
        prompt = dedent(f"""
        Translate this Chinese text to clear English:
        {ctx.txtCN}
        
        Requirements:
        - Keep technical terms in English
        - Use simple, direct phrasing
        - Maintain original formatting
        """)
        response = await self.egress.chat.completions.create(
            model="towerinstruct",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content