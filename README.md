# 🌐 Fortytwo

**Fortytwo** — это распределённая нейросетевая вычислительная сеть, где каждый участник (нода) выполняет LLM-инференсы и участвует в коллективной оценке ответов, получая вознаграждение за вычисления и качество результатов.

---

## 🧩 Обзор: "что под капотом"

Fortytwo — это не одна ИИ-система, а целая глобальная LLM-сеть, в которой:

- каждый участник запускает свою модель (**Capsule**)
- ноды объединяются в **Inference-раунды**
- после генерации ответа они **оценивают друг друга**
- система находит **консенсус** — чей ответ лучший
- лучшие получают **рейтинг** и **оплату**

---

## 📦 Компоненты Fortytwo

| Компонент           | Назначение                                                                 |
|---------------------|----------------------------------------------------------------------------|
| `Capsule`           | Отвечает за запуск LLM и обработку запросов                              |
| `Protocol Node`     | Участвует в сети: слушает Intent'ы, участвует в раундах, проверяет хэши  |
| `Utils`             | Вспомогательные утилиты: создание аккаунта, восстановление по seed и др. |
| `model_cache`       | Локальное хранилище выбранной GGUF-модели                                 |
| `.account_private_key` | Приватный ключ для подписи и взаимодействия с сетью                     |

---

## 🔄 Как это работает (пошагово)

1. **Сеть создаёт новый запрос (Intent)**
   - Кто-то отправляет текстовый запрос
   - Он становится `IntentCreatedV3`

2. **Protocol ловит Intent, Capsule генерирует ответ**
   - Capsule обрабатывает его (например, с Qwen3-8B)
   - Ответ шифруется и отправляется в сеть

3. **Decrypt Round**
   - Capsule'ы обмениваются зашифрованными результатами
   - Участвуют в расшифровке чужих ответов
   - Оценивают качество чужих ответов (ранжирование)

4. **Формирование консенсуса**
   - Проверка хэшей
   - Подпись результатов
   - Определяется лучший ответ

5. **Получение рейтинга**
   - В логах: `Node ratings updated!`
   - Чем выше рейтинг — тем больше задач и наград

---

## 🧠 Жизненный цикл узла (стейты)

| Состояние                | Действие узла                                      |
|--------------------------|---------------------------------------------------|
| `InferenceJoin`          | Присоединяется к новому раунду                    |
| `InferenceRound`         | Генерирует ответ с помощью LLM                   |
| `InferenceDecryptRound`  | Получает и расшифровывает ответы других          |
| `RankingRound` (скрыт)   | Голосует за лучшие ответы                         |
| `Finalization`           | Подтверждает финальные хэши                      |

---

## 💰 Вознаграждение

Ноды получают **рейтинг** и **оплату** за успешные раунды.

Учитывается:

- ⏱ **Скорость ответа**
- 🎯 **Качество** (если твой ответ выбран)
- ⏰ **Своевременность** (не проспал дедлайн)

---

## 📊 Что можно увидеть в логах

| В логах                          | Что это значит                        |
|----------------------------------|---------------------------------------|
| `IntentCreatedV3`                | Появилась новая задача                |
| `Inference request sent with ID:`| Ты отправил свой ответ                |
| `Node ratings updated!`          | Получил очки / оценку                 |
| `rankings:`                      | Участвовал в голосовании              |

---

## ⚙️ Под капотом

- 💾 **LLM-модели**: формат GGUF, запуск через `llama.cpp`
- 🔐 **Голосование**: threshold signatures + consensus voting
- 🦀 **Инфра**: Rust-бинарники, встроенный протокол (закрытый)
- 🌐 **Коммуникация**: P2P, возможно на базе `libp2p`
- 📡 **REST-эндпоинты**: для мониторинга и отладки

---

### Установка на Linux Ubuntu 22.04 и 24.04

на почту после заполнения формы должен прийти код (от отправителя operators@paracosm.fortytwo.network), при помощи которого создайтся кошелёк
```bash
apt update && apt install -y libgomp1 curl unzip tmux
```
```bash
tmux new -s FourtyTwo
```
Проверяем поддерживает ли проц набор необходимых инструкций
```bash
lscpu | grep -iE 'avx|sse|aes'
```
```bash
mkdir -p ~/Fortytwo && cd ~/Fortytwo
```
```bash
curl -L -o fortytwo-console-app.zip https://github.com/Fortytwo-Network/fortytwo-console-app/archive/refs/heads/main.zip
unzip fortytwo-console-app.zip
cd fortytwo-console-app-main
chmod +x linux.sh && ./linux.sh
```
Приватник тут ```/root/Fortytwo/fortytwo-console-app-main/FortytwoNode/```  с именем ```.account_private_key```

Модель                          | Файл (Q4_K_M)                     | Вес (≈ GB)
-------------------------------|-----------------------------------|------------
unsloth/Qwen3‑1.7B‑GGUF        | Qwen3‑1.7B‑Q4_K_M.gguf            | ~1.7 GB (≈1.7B params)
unsloth/Qwen3‑8B‑GGUF          | Qwen3‑8B‑Q4_K_M.gguf              | ≈4.7 – 4.9 GB³
unsloth/Qwen3‑14B‑GGUF         | Qwen3‑14B‑Q4_K_M.gguf             | ≈9 GB⁴
unsloth/Llama‑4‑Scout‑17B‑16E  | Llama‑4‑Scout‑17B‑Q4_K_M (part 1) | ~9‑10 GB (в 2 частях)
unsloth/Qwen3‑30B‑A3B‑GGUF     | Qwen3‑30B‑A3B‑Q4_K_M.gguf         | ≈18.6–18.7 GB²
unsloth/Qwen3‑32B‑GGUF         | Qwen3‑32B‑Q4_K_M.gguf             | ≈19.8 GB (≈20 GB) :contentReference[oaicite:1]{index=1}
bartowski/open‑r1_OlympicCoder‑32B‑GGUF | open‑r1_OlympicCoder‑32B‑Q4_K_M.gguf | ≈19‑20 GB (MoE 32B ≈ как Qwen3)¹
bartowski/THUDM_GLM‑Z1‑32B‑0414‑GGUF   | THUDM_GLM‑Z1‑32B‑Q4_K_M.gguf      | ≈19–20 GB (32B MoE, аналогично)
bartowski/agentica‑org_DeepCoder‑14B‑Preview‑GGUF | DeepCoder‑14B‑Preview‑Q4_K_M.gguf | ≈9–10 GB (14B quant)
jedisct1/MiMo‑7B‑RL‑GGUF      | MiMo‑7B‑RL‑Q4_K_M.gguf            | ~3‑4 GB (7B params, quantized)⁵
bartowski/nvidia_OpenMath‑Nemotron‑14B‑GGUF | OpenMath‑Nemotron‑14B‑Q4_K_M.gguf | ≈9–10 GB (14B quant)
irmma/DeepSeek‑Prover‑V2‑7B‑Q4_K_M‑GGUF  | deepseek‑prover‑v2‑7b‑q4_k_m‑imat.gguf | ~3–4 GB
unsloth/gemma‑3‑4b‑it‑GGUF     | gemma‑3‑4b‑it‑Q4_K_M.gguf         | ~2.5‑3 GB (4B quant)
bartowski/Tesslate_Tessa‑Rust‑T1‑7B‑GGUF | Tesslate_Tessa‑Rust‑T1‑7B‑Q4_K_M.gguf | ~3‑GB
bartowski/open‑r1_OlympicCoder‑7B‑GGUF | open‑r1_OlympicCoder‑7B‑Q4_K_M.gguf | ~3–4 GB (7B quant)


## 🔗 Полезные ссылки

| Ресурс             | Ссылка                                                                 |
|--------------------|------------------------------------------------------------------------|
| 🌐 Официальный сайт | [fortytwo.network](https://fortytwo.network)                           |
| 🚀 Форма     | [Форма на старт ноды](https://tally.so/r/wQzVQk)                 |
| 📚 Гайды и доки    | [Официальная документация](https://docs.fortytwo.network/docs/quick-start) |
| 📊 Дашборд         | [Смотреть статус ноды](https://fortytwo.network/dashboard)             |
| 📦 GitHub          | [fortytwo-console-app](https://github.com/Fortytwo-Network/fortytwo-console-app) |
| 🗨️ Discord         | [discord.gg/fortytwo](https://discord.com/invite/fortytwo)             |
| 🐦 Twitter / X     | [@fortytwonetwork](https://x.com/fortytwonetwork)                      |
| 🛡️ Гильдия         | [guild.xyz/fortytwo](https://guild.xyz/fortytwo-d9acb1)                |
| 🌏 Эксплорер        | [Вкладка Activity](https://testnet.monadexplorer.com)                |

---





