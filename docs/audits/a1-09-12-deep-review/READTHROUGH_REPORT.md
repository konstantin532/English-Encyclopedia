# A1 9–12 — независимое чтение (не внедрение)

Baseline `5826785ee3f665fac765783ba9a95a5dd3b52655`; detached worktree `/tmp/ee-a1-09-12-readthrough`. Рабочее дерево чистое.

Найдены 20 групп подтверждённых проблем. Полные before/proposed_after и сценарии в JSON; это не заявление, что курс принят.

## N01: methodological sequence
`content/seed_lessons/a1_w06_l11_present_simple.yaml` — `{'slug': 'a1-present-simple-i-you', 'layer': 6}`.
Следующий урок12 посвящён времени; -s вводитсяL13. Ложный указатель мешает найти объяснение.
Проверка: Проверить реальную карту L11→L12→L13, оставить общий мост I/you→he/she.

## N02: overgeneralization / cross-source contradiction
`content/seed_lexicon/a1_w05_shop.yaml` — `{'uid': 'LX-00108'}`.
Сам урок9 уже объясняет порции, словарь по-прежнему подаёт запрет. Русское «два молока» тоже может означать упаковки; жёсткая калька не разграничивает значения.
Проверка: Сопоставить substance vs serving; не принимать a milk для задания, явно требующего вещество.

## N03: unprepared vocabulary
`content/manifests/a1_scaffold_transfer.json` — `{'slug': 'a1-there-is-some', 'step': 3}`.
Any introduced onlyA1+week7/LX00733; L9 requires producing it without preparation. Same futureword in understanding transfer model.
Проверка: Use compiled guide and cold-transfer models; no any requirement atL9.

## N04: unprepared vocabulary
`content/manifests/a1_understanding_checks.json` — `{'slug': 'a1-there-is-some', 'skill': 'transfer'}`.
Согласовать сN03, сохранив вопрос+просьбу. Some water не обязательно мало, поэтому условие «немного» можно заменить на «воды, не уточняя объём».
Проверка: Cold independent task uses onlyintroducedwater/some, not any.

## N05: unprepared vocabulary
`content/manifests/a1_scaffold_transfer.json` — `{'slug': 'a1-how-much-prices'}`.
Ticket introducedweek14, jacketweek10. Neither prepared here; replacewithknownfood/objects rather thanmovelevelscope.
Проверка: No ticket/jacket in L10requiredmodels; preserve3steps/2variants distinctbaseline model.

## N06: unprepared vocabulary
`content/manifests/a1_scaffold_transfer.json` — `{'slug': 'a1-present-simple-i-you'}`.
Saturdays/read introducedweek10. Replacewithoutinventingnewunits orunknownweekdays.
Проверка: No Saturday/read in cold L11models; retain questions+assertion.

## N07: narrow answer inventory
`content/seed_lessons/a1_w05_l09_there_is.yaml` — `{'uid': 'EX-00047'}`.
Полные ответы сwateralreadyaccepted; contractedfullanswerisvalid. Нельзя сокращать bareYes there is, но здесьпослеis естьwater.
Проверка: RealAPI: acceptlistedforms; rejectwrongnumber/negation/subject orwrongwordorderwhenrequested. Nonmatchingopenresponseisneeds_review, notproofwronggrammar.

## N08: narrow answer inventory
`content/seed_lessons/a1_w05_l10_how_much.yaml` — `{'uid': 'EX-00053'}`.
Цифра5 передаёт ровно тужецену и сохраняетполноеThey-предложение; отвергатьдругиечисла.
Проверка: RealAPI: acceptlistedforms; rejectwrongnumber/negation/subject orwrongwordorderwhenrequested. Nonmatchingopenresponseisneeds_review, notproofwronggrammar.

## N09: narrow answer inventory
`content/seed_lessons/a1_w06_l11_present_simple.yaml` — `{'uid': 'EX-00061'}`.
КоординациясобщимIпередаётобадействия; существующийacceptedуже допускаетand, поэтому требование«двумяфразами»неисключаетсоюз.
Проверка: RealAPI: acceptlistedforms; rejectwrongnumber/negation/subject orwrongwordorderwhenrequested. Nonmatchingopenresponseisneeds_review, notproofwronggrammar.

## N10: narrow answer inventory
`content/seed_lessons/a1_w06_l12_time.yaml` — `{'uid': 'EX-00065'}`.
Число8неизменяетвремя; существующийacceptedуже допускаетAt8, но полныйответсцифройнеизвестенключу.
Проверка: RealAPI: acceptlistedforms; rejectwrongnumber/negation/subject orwrongwordorderwhenrequested. Nonmatchingopenresponseisneeds_review, notproofwronggrammar.

## N11: narrow independent answer inventory
`content/manifests/a1_understanding_checks.json` — `{'slug': 'a1-how-much-prices', 'skill': 'writing'}`.
Prompt«Этостоиттридоллара»незадаётit; Exercise.normalizeне раскрываетсокращения. Неизвестнаяформастановитсяneeds_reviewвместоknownmatch.
Проверка: SubmitthroughindependentAPIandpreservewrongnumber/negationrejection; no globalapostropheexpansion.

## N12: false lexical progress
`content/seed_lessons/a1_w05_l09_there_is.yaml` — `{'slug': 'a1-there-is-some'}`.
record_attempt/record_practiceсоздаютUnitProgressдлякаждогоunitsID независимо оттогоупотреблена лифраза. Много постороннихготовыхфраз: молоковопросvsутверждение/ценавопросvsответ/подъёмvsсон/clockquestionvsgetup. Предложеныузкиепривязки; EX63одинответatнедоказываетвсюготовуюфразуIgetupatfive. Условныйпустойunitsсписокбезновойлексемыбезопаснее; добавлениеatUID00023требуетотдельносверитьтемпоральноезначениетаккаксейчаслексиконописываетместо.  Для EX59YesIdo emptyunitsдопустимовместозачётаwork/every.
Проверка: Realauthenticatedmain/practiceAPI: correctanswercreatesonlyjustifiedunitprogress; nofuturefalsephrasecredit; wronganswerdoesnotmarkmastery. Existinghistoryunchanged.

## N13: false lexical progress
`content/seed_lessons/a1_w05_l10_how_much.yaml` — `{'slug': 'a1-how-much-prices'}`.
record_attempt/record_practiceсоздаютUnitProgressдлякаждогоunitsID независимо оттогоупотреблена лифраза. Много постороннихготовыхфраз: молоковопросvsутверждение/ценавопросvsответ/подъёмvsсон/clockquestionvsgetup. Предложеныузкиепривязки; EX63одинответatнедоказываетвсюготовуюфразуIgetupatfive. Условныйпустойunitsсписокбезновойлексемыбезопаснее; добавлениеatUID00023требуетотдельносверитьтемпоральноезначениетаккаксейчаслексиконописываетместо.  Для EX59YesIdo emptyunitsдопустимовместозачётаwork/every.
Проверка: Realauthenticatedmain/practiceAPI: correctanswercreatesonlyjustifiedunitprogress; nofuturefalsephrasecredit; wronganswerdoesnotmarkmastery. Existinghistoryunchanged.

## N14: false lexical progress
`content/seed_lessons/a1_w06_l11_present_simple.yaml` — `{'slug': 'a1-present-simple-i-you'}`.
record_attempt/record_practiceсоздаютUnitProgressдлякаждогоunitsID независимо оттогоупотреблена лифраза. Много постороннихготовыхфраз: молоковопросvsутверждение/ценавопросvsответ/подъёмvsсон/clockquestionvsgetup. Предложеныузкиепривязки; EX63одинответatнедоказываетвсюготовуюфразуIgetupatfive. Условныйпустойunitsсписокбезновойлексемыбезопаснее; добавлениеatUID00023требуетотдельносверитьтемпоральноезначениетаккаксейчаслексиконописываетместо.  Для EX59YesIdo emptyunitsдопустимовместозачётаwork/every.
Проверка: Realauthenticatedmain/practiceAPI: correctanswercreatesonlyjustifiedunitprogress; nofuturefalsephrasecredit; wronganswerdoesnotmarkmastery. Existinghistoryunchanged.

## N15: false lexical progress
`content/seed_lessons/a1_w06_l12_time.yaml` — `{'slug': 'a1-time-at-seven'}`.
record_attempt/record_practiceсоздаютUnitProgressдлякаждогоunitsID независимо оттогоупотреблена лифраза. Много постороннихготовыхфраз: молоковопросvsутверждение/ценавопросvsответ/подъёмvsсон/clockquestionvsgetup. Предложеныузкиепривязки; EX63одинответatнедоказываетвсюготовуюфразуIgetupatfive. Условныйпустойunitsсписокбезновойлексемыбезопаснее; добавлениеatUID00023требуетотдельносверитьтемпоральноезначениетаккаксейчаслексиконописываетместо.  Для EX59YesIdo emptyunitsдопустимовместозачётаwork/every.
Проверка: Realauthenticatedmain/practiceAPI: correctanswercreatesonlyjustifiedunitprogress; nofuturefalsephrasecredit; wronganswerdoesnotmarkmastery. Existinghistoryunchanged.

## N16: lexical overgeneralization
`content/seed_lexicon/a1_w06_day_plus.yaml` — `{'uids': ['LX-00305', 'LX-00306', 'LX-00310']}`.
Watchнеограничиваетсядвижущимсяобъектом;listenдопускаетбезобъектноеупотребление;dinnerнеуниверсально18–19часов. Урок12ужеотрицаетобщеерасписаниеСША,словарьпротиворечит.
Проверка: ReadlexiconcardalongsideL11/L12; constrainlessonmeaningwithoutdeclaringalternativeswrong.

## N17: contextually valid distractor
`content/manifests/a1_micro_review_09_12.json` — `{'slug': 'a1-there-is-some', 'exercise_order': 1}`.
There is milk?возможнокакудивлённыйпереспрос,небезусловнаяошибка. Все5кейсовнаследуютнеуточнённоеусловие. Необходимаформулировкасхемы,неискусственныйзапрет.
Проверка: Compileactual5cardsandexerciseAPI; verifycontextualreasonforwrongchoiceandkeypositionrotationsunchanged.

## N18: wrong contextual markers
`content/seed_poems/p03_what_time_is_it.yaml` — `{'number': 3}`.
TenanswersWhattimeisit→clockN3. Go to work meansgoingtoworkplace;workhereisnoun,notbareverb. Registryvaluesunchanged; targetuidworkverb006? LX00128currentlyverbshouldnotautomaticallygive masteryofnounsense. Need nounmeaninglayerorpreparedphrasewithoutnewIDs.
Проверка: ActualpoemHTMLTenlabelClocktime, worknounlabel; English/IPA/gapsunchanged; assess lexicaltargetnounmeaningwithoutIDrepurpose.

## N19: unprepared vocabulary in micro review
`content/manifests/a1_micro_review_09_12.json` — `{'slugs': ['a1-there-is-some', 'a1-present-simple-i-you']}`.
Whiteintroducedweek12LX00237;read/walkweek10. Alsoread appearsotherL11microcases3,6:rewriteallconsistentcases,notonlyshownsamples. L9layer6colorlistwhitealsofuture;removefromlist ratherthanmovelexicalID.
Проверка: Allgeneratedcardsvocabknownlessoncutoff; compare5distinctpromptsstillholds.

## N20: wrong phonetic metadata
`content/seed_weeks/a1_w05.yaml` — `{'week': 5, 'twister': 5}`.
ae означает /æ/, но в тексте и IPA скороговорки5 этого звука нет. Упражнение фактически сравнивает /ɪ/ и /i/ плюсзвонкийth; дляпарыгласныхнетготовогоHINTSкода. Не вводитьновыефонетическиекодывэтойправке, снятьложныйae.
Проверка: Loadtwistermetadataandassert all claimedhintIPAoccursin targetlinewherevalid; preserve text/IPA/audio. Не утверждатьчтоэтоlabelпоказывалсяученику: точныйфронтендпутьfocus_soundsнеподтверждён.

## Реальные связи и зависимости
L9–10 — week5 shop; L11–12 — week6 day. Week6 assigned story2 The Café on the Corner и poem3 What Time Is It? через course_map.yaml. Week5 не имеет отдельной истории/стиха.
L9: be/plural/articles→there is/are/some→colors. L10: knownnumbers→price is/are→dollars. L11: I/you→do questions/negation→routine verbs→at clock bridge; L12: clock it vs at event/in parts of day→meals. He/she -s detail belongs L13, not L12.
Relevant actual micro data overrides fallback topics: mistake_review.question_bank() loads themed topic packs then micro_bank(); editing only fallback will not fix rendered micro cards.
Story2 uses comes/drinks/has beforeL13 and narrativeI go/I drink for eventsequence. Нужен короткий честный подготовительный мост: распознать3-е лицо по введённомуL11краткомупункту, и обозначитьисторическоенастоящееврассказе отдельно отобычнойпривычки. Не объявлятьповествовательноенастоящееграмматическойошибкой.
Poem3 has again with no exact lemma anywhere; comes in before spatialin detailed week8; explain prepared chunks before asking production. Do not claimaudioalignedwithoutactualrecordings.
LexiconL11 watch/listen examples use in the evening introducedL12: permissible as fulltranslatedpreview, notcoldindependentrequirementbeforeexplanation. L11active prompt Iworkinthemorning tests it beforeL12; either addshortbridgeoruseeveryday.

## Прочитанные материалы
All4lessonYAML (7layers,24mainexercises,16translations); week5/6 scripts, twisters,goals; lexiconshop/shopplus/day/dayplus/in/story02; understanding/scaffold four entries; active topics09_13 four entries; scenarios07_12 four entries; errorrepairs01_18 fourentries; all24micro specs120compiledcases; fallback20cards; story2andpoem3fully.
AGENTS/CLAUDE; relevantsectionsweeksspec/plan/journal; registry; checker/services/microcompiler/understanding source. OtherAGENTS/CLAUDEonlyarchivessnapshot,notapplicablecataloginstructions.
a1_retry_guidance.json contains no lesson9–12specificentries; runtimefallbackusesgenericguidance. No unavailablemodulewasassumedpresent.

## Пределы проверки
- No repository edits, migrations, DB connection, full tests, browser or audio listening performed.
- Pure model checking ran with explicit isolated SQLite settings; no database query was needed.
- Proposals require implementation review, exact current-before comparison, vocabulary gates and regression tests.
- Do not treat a finite open-response mismatch as grammatical incorrectness.
