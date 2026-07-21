    @bot.command(name="اوامر", aliases=["help", "الأوامر", "commands"])
    async def custom_help(ctx):
        """عرض جميع الأوامر المتاحة في البوت تلقائياً"""
        embed = discord.Embed(
            title="📜 قائمة أوامر البوت",
            description="جميع الأوامر المتاحة حالياً في السيرفر (تتحدث تلقائياً عند إضافة أي أمر جديد):",
            color=discord.Color.blue()
        )
        
        # تجميع الأوامر المتاحة وترتيبها
        commands_list = []
        for command in bot.commands:
            # تخفيض الأوامر المخفية أو الأوامر النظامية إذا أردت
            if not command.hidden:
                # جلب اسم الأمر ووصفه إن وجد
                desc = command.help or "لا يوجد وصف"
                commands_list.append(f"• **`{command.name}`** : {desc}")
        
        if commands_list:
            embed.add_field(name="✨ الأوامر المتوفرة", value="\n".join(commands_list), inline=False)
        else:
            embed.description = "لا توجد أوامر مسجلة حالياً."
            
        embed.set_footer(text=f"مطلوب بواسطة {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
