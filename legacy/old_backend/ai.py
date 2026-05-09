import asyncio

from httpx import AsyncClient
from model import StyleAdjustmentResponse
from openai import AsyncOpenAI
from openai.types.chat import ParsedChatCompletion

# import openai

word_prompt = (
    "角色定义:\n"
    "你是一位专业的语言编辑和校对员，精通多种语言的细微差别。你的任务是仔细审查用户提供的文本，找出其中用词不当（inappropriate word usage）的地方。\n"
    "任务说明:\n"
    "识别: 找出文本中可能存在语义错误、语境不符、表达笨拙、不够精确、风格不一致（例如，过于口语化或过于书面化）或可以有更佳选择的词语或短语。\n"
    "定位: 明确指出每个被识别出的词语或短语在原文中的具体位置。使用上下文片段来帮助定位。\n"
    "替换: 为每个识别出的问题词语提供 2-4 个更合适的替换选项。\n"
    "解释: 简要说明为什么原始用词不当，以及为什么建议的替换选项更好（例如，更精确、更符合语境、更流畅、更符合语气等）。\n"
    "语言: 准备好处理任何语言的文本，并使用与原文相同的语言进行分析和建议（除非原文混用多种语言，此时可用英语或用户指定的语言进行解释）。\n"
    "格式：不要添加任何解释、评论、道歉或标记（除非用户明确要求对改动进行说明）。直接给出干净的、可以直接使用的修正结果。如果有多个候选，分开成多个条目。\n"
    "待分析文本:\n"
    "{0}"
)

syntax_prompt = (
    "# 角色\n"
    "你是一位精通多种语言的语法和校对专家。\n"
    "# 任务\n"
    "你的核心任务是仔细检查用户提供的文本，识别并修正其中的语法错误、拼写错误、标点符号使用不当以及表达不清或不自然的地方。\n"
    "# 指令\n"
    "1.  **语言自适应**: 用户提供的文本**可能是任何语言**（例如英语、中文、西班牙语、法语、日语等）。你需要自动识别文本的语言，并根据该语言的语法规则进行修正。\n"
    "2.  **修正范围**:\n"
    "*   修正明显的语法结构错误（如动词时态、主谓一致、名词单复数、词序等）。\n"
    "*   修正拼写错误。\n"
    "*   修正不恰当或缺失的标点符号。\n"
    "*   改进少量因语法问题导致的表达笨拙或不清晰之处，使其更自然流畅。\n"
    "3.  **忠于原意**: 在修正过程中，**务必保持文本的原始核心含义和意图不变**。避免进行主观性的、大幅度的内容改写或风格调整。你的目标是修正错误，而不是重写文本。\n"
    "4.  **输出格式**: 不要添加任何解释、评论、道歉或标记（除非用户明确要求对改动进行说明）。直接给出干净的、可以直接使用的修正结果。如果有多个候选，分开成多个条目。\n"
    "5.  **效率**: 快速准确地完成修正。\n"
    "# 示例交互\n"
    '用户输入: "He dont know what to did yesterdey."\n'
    '你的输出: "He didn\'t know what to do yesterday."\n'
    '用户输入: "我明天去了商店如果天气好。"\n'
    '你的输出: "如果天气好，我明天就去商店。"\n'
    "请准备好处理用户接下来输入的任何语言的文本，并进行语法修正。\n"
    "{0}"
)

style_prompt = (
    "角色: 你是一位专业的文风编辑与转换专家。\n"
    "核心任务: 你的主要职责是根据用户指定的目标文风，修改用户提供的原始文本。你需要准确理解原始文本的核心意义和关键信息，并在保持这些内容不变的前提下，调整文本的风格。\n"
    "关键能力:\n"
    "理解与保持: 深入理解原始文本的含义、意图和关键信息点，确保在修改文风后这些核心内容不丢失或被歪曲。\n"
    "风格识别与转换: 能够识别并应用各种不同的写作风格，包括但不限于：正式、非正式（口语化）、幽默、严肃、学术、简洁、华丽、客观、主观、特定人物/作品的模仿风格等。\n"
    "语言适应性: 能够处理不同语言的文本（尽管你的主要交互语言可能是中文，但要能理解并尝试修改非中文文本的风格）。修改时，尽量使用目标风格在该语言中对应的表达习惯。\n"
    "细致调整: 调整的方面应包括：词汇选择、句子结构与长度、语气语调、段落组织、以及整体的流畅度和表达方式。\n"
    "工作流程:\n"
    "接收用户提供的原始文本。\n"
    "接收用户明确指定的目标文风描述（例如：“请把这段话改得更正式一些”、“让这段文字读起来更像日常对话”、“模仿莎士比亚的风格重写这段描述”）。\n"
    "分析原始文本和目标文风的要求。\n"
    "进行文风转换，生成修改后的文本。\n"
    "输出修改后的文本给用户。\n"
    "与用户的互动:\n"
    "在输出结果时，可以简要说明为了达到目标文风主要做了哪些调整（可选）。\n"
    "重要原则:\n"
    "忠于原文意义: 文风修改不应改变事实信息或核心观点。\n"
    "贴合目标风格: 修改后的文本应显著体现出用户所要求的目标文风特征。\n"
    "自然流畅: 无论何种风格，修改后的文本都应自然、流畅、易于理解。\n"
    "请准备好接收用户的原始文本和目标文风指令，并开始你的文风修改工作。\n"
    "文风：{0}\n"
    "内容：{1}"
)


def format_word_prompt(text: str) -> str:
    return word_prompt.format(text)


def format_syntax_prompt(text: str) -> str:
    return syntax_prompt.format(text)


def format_style_prompt(style: str, text: str) -> str:
    return style_prompt.format(style, text)


class AIClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=AsyncClient(proxy="socks5://localhost:10808"),
        )

    async def generate_response(self, prompt: str) -> ParsedChatCompletion:
        response = await self.client.chat.completions.create(
            model=self.model,
            stream=False,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        return response

    async def generate_response_format(
        self, prompt: str, formating
    ) -> ParsedChatCompletion:
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            # temperature=0.7,
            response_format=formating,
        )
        return response


class AIConfigManager:
    def __init__(self):
        self._api_key: str | None = None
        self._model: str | None = None
        self._base_url: str | None = None
        self._active_client: AIClient | None = None
        self._lock = asyncio.Lock()  # Crucial for concurrency safety
        self._config_version = 0  # Track changes

    async def update(
        self,
        api_key: str,
        model: str,
        base_url: str,
    ):
        async with self._lock:
            if (
                self._active_client is None
                or api_key != self._active_client.api_key
                or model != self._active_client.model
                or base_url != self._active_client.client.base_url
            ):
                print(
                    f"Updating API key or model. Old: {self._api_key}, New: {api_key}"
                )

                self._active_client = AIClient(
                    api_key=api_key, model=model, base_url=base_url
                )
                self._config_version += 1

    async def get_client(self) -> AIClient | None:
        async with self._lock:
            return self._active_client

    def get_current_config_info(self) -> dict:
        # No lock needed for read-only info if atomicity isn't critical here
        return {
            "current_api_key_suffix": (
                f"...{self._api_key[-4:]}" if self._api_key else None
            ),
            "current_model": self._model,
            "current_base_url": self._base_url,
            "config_version": self._config_version,
            "client_instance_id": (
                id(self._active_client) if self._active_client else None
            ),
        }


async def main():
    # base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # model = "gemini-2.0-flash-thinking-exp-01-21"
    # api_key = "0b755452512d486c974e27ba20721a44"
    api_key = "15c7cc86cc4e44aa978cbbebd70f7975"
    base_url = "https://genaiapi.shanghaitech.edu.cn/api/v1/start"
    model = "deepseek-v3:671b"

    client = AIClient(api_key=api_key, model=model, base_url=base_url)
    # prompt = "What is the capital of France?"

    # response = await client.generate_response_format(
    #     word_prompt.format(
    #         "上个星期天，我和朋友们一起去公园玩耍。那天的气候特别好，阳光很激烈。我们在草地上放置了一块野餐布，然后开始享受我们的午餐。我带了自己做的三明治，味道非常可爱。吃完饭，我们决定去湖边看看风景。湖水很清洁，还能看到几只鸭子在水里游泳。我们还瞻仰了公园里的一个小纪念碑。下午，我们感觉有点疲倦，就决定结束这次愉快的集会回家了。这次出门真是让人心情舒畅。"
    #     ),
    #     CorrectionResponse,
    # )
    # for i in response.parsed.corrections:
    #     print(i)

    # response = await client.generate_response_format(
    #     syntax_prompt.format(
    #         "昨天在公园里面，那个很高兴的小狗看见我，它跑得很快地，因为它想吃我的方便面条，所以我没给他了。"
    #     ),
    #     CorrectionResponse,
    # )
    # for i in response.parsed.corrections:
    #     print(i)

    response = await client.generate_response(
        style_prompt.format(
            """关于推动我市数字经济与实体经济深度融合发展的若干情况汇报
（摘要）
尊敬的各位领导：
为贯彻落实党中央、国务院关于发展数字经济的战略部署，以及省委省政府相关工作要求，围绕市委市政府提出的“建设高水平数字经济强市”目标，近期，我（单位名称，例如：市发展和改革委员会）就我市数字经济与实体经济融合发展情况进行了专题调研。现将主要情况汇报如下：
一、 基本情况与主要成效
近年来，我市高度重视数字经济发展，坚持以数字化转型整体驱动生产方式、生活方式和治理方式变革。一是政策体系不断完善。 先后出台了《[城市名称]市促进数字经济发展条例》、《关于加快工业互联网创新发展的实施意见》等一系列政策文件，为融合发展提供了有力保障。二是基础设施持续升级。 5G网络、数据中心、工业互联网标识解析二级节点等新型基础设施建设布局加快，算力支撑能力显著提升。三是融合应用初见成效。 在智能制造、智慧农业、现代服务业等领域涌现出一批典型应用场景和示范项目，部分骨干企业数字化、网络化、智能化水平明显提高，初步形成了以点带面的良好发展态势。数据显示，[选择性提及一两个宏观数据，例如：2023年全市数字经济核心产业增加值占GDP比重达到X%，制造业关键工序数控化率达到Y%]。
二、 面临的挑战与问题
在肯定成绩的同时，我们也清醒地认识到，我市数字经济与实体经济融合发展仍面临一些亟待解决的问题：一是融合深度有待加强。 部分中小企业数字化转型意愿不强、能力不足，“不愿转、不敢转、不会转”的问题依然存在。二是数据要素价值释放不充分。 数据壁垒、数据安全、数据标准统一等问题制约了数据要素的有效流通和应用。三是高端人才和复合型人才供给不足。 既懂技术又懂产业的跨界人才缺口较大，成为制约融合创新的瓶颈。
三、 下一步工作建议
为进一步推动我市数字经济与实体经济深度融合，实现高质量发展，建议下一步重点抓好以下工作：
强化顶层设计与政策协同。 进一步优化完善融合发展政策体系，加强跨部门协调联动，形成工作合力。
加快关键核心技术攻关。 聚焦工业软件、高端芯片、人工智能等领域，支持产学研用联合攻关，提升自主创新能力。
深化分行业、分领域融合应用。 聚焦重点产业链，打造一批数字化转型标杆企业和示范园区，推广成熟解决方案。
夯实数据基础和安全保障。 探索建立数据产权、流通交易、收益分配、安全治理等基础制度，筑牢数字安全屏障。
加大人才引育力度。 完善人才培养、引进、评价和激励机制，打造高水平数字技术工程师和复合型人才队伍。
我们相信，在市委市政府的坚强领导下，通过全市上下的共同努力，我市数字经济与实体经济融合发展必将迈上新台阶，为经济社会高质量发展注入强大动力。
妥否，请审示。
[汇报单位名称，例如：市发展和改革委员会]
[日期，例如：2024年X月X日]""",
            "小学生作文，但保留专业词汇",
        ),
        # StyleAdjustmentResponse,
    )
    print(response)
    print(response.parsed.result)
    print(response.parsed.reasons)


if __name__ == "__main__":
    # Example usage

    asyncio.run(main())
