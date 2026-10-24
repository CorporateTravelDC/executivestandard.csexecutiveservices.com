# Article ledger

Every Executive Standard article, as SHA-256 of its canonical source, the date it was first
committed, and its slug -- without the text. Dates are when the canonical file entered this repository (the 2026-09-08 consolidation for older pieces), not the original Substack publication (the full edition is for members). Signed by the
publisher's key (ARTICLE-LEDGER.md.asc). A reader holding an article can check it is the
one that was published, unaltered, and when.

Two sources are listed, each hashed as committed: `articles/` holds the article body,
`_md/` the published source with its front matter. A slug in both hashes differently
by design; check a copy against the block it came from.

## `articles/*.md`

```
60fedaf980547f865873ea01d268bb35d18de7c46e15f1c1f6ad52a8aaeb4e5a  2026-09-29  default-on-is-not-consent
7ef959ded8ea639811765e589d644e88f711f059c0b7d9387f0b9a2bfaa93670  2026-09-08  even-the-guy-driving-your-uber-can
59a46272dfe9888c818fea9ecc51ef637d83cd21a77d0286990bc061d05ebc9b  2026-09-08  executive-protection
ceb25765ac13be7b3f3a262ca96e172e6a830499a585cf817e3e17e7bfd3a0df  2026-09-08  i-drove-through-surge-for-a-year
6d1987c869d55f5d9a8b08d89e342be1d9190e8561f444db114018402f4cbfb8  2026-09-08  only-the-writer-went-dark
a1d9c467dddb00da268ce707b3ce2e231de71d791551c4253e55df5c93725528  2026-09-15  own-your-dns-or-someone-else-will
327c8bce44debde331b6bca938470cdd54261b1570ccb0362bd9e670640121ee  2026-09-08  same-ride-same-minute-two-different
72538b5e04dcb113e701a16a4d4984f1c9d98ef6d9002f7f1069dbd26644e0e0  2026-09-08  see-where-you-tap
ed95bcce343aac7b310186423eaf3c8bbe751984284da0084b54d33cc3a4a2f2  2026-09-08  skills-are-not-systems
5f8c5d2f1a0c95dad76478522ce3308d25f1b62268d348a2342efe40d4a8eb94  2026-09-08  teaser-own-your-dns
75a347b6bdadca009bb99c34c32ee425a63bb83171be5a9a386fede73128bcc9  2026-09-08  the-access-no-one-bothered-to-earn
60191aaecdfacd48945275d188d472fa6d144aeece0f6c2ba41bcbad75881bc2  2026-09-18  the-checkpoint-you-build-yourself
7da39c84b312e28927235c3d0d50c61008d4bcb510f4f6b0616f1b9973b953f4  2026-09-08  the-four-hundred-dollar-experiment
158781b3553a8b15950d182402dbc84d0b852075be59a95daa55620b475f7b4d  2026-10-03  the-house-always-publishes-its-odds
0e41c13a862f407da7c5627110bcf4e071b26a7f7666e933b83d98d3bf143476  2026-09-29  the-landing-that-never-happened
b343bb631b22afddbbd6894666163914b6e8c26c7e6da5c78ead214963743def  2026-09-08  the-machine-in-the-closet
adb1533ae97cee6c5ec2997cc1bbf13945df61ec8df5347e40a712ebcafe212b  2026-09-25  the-new-hire-you-dont-hand-the-keys
9a44b1fd83ef0c0cbde1494d6efcfb0ba9e44d2b9bf8fe34270710617b8240de  2026-09-09  the-quiet-perimeter-tscm-digital-opsec
7d5dab2d5f7dfb4b23335ac64906dd8fb430b06ceb36bfc12809236dbd3214e2  2026-09-08  the-squeeze-isnt-the-goal-its-the
f111fd9754512e086e565c870c8bfc96fe7079129e8de8f8b8cbd82f39cda1b0  2026-09-08  the-tell-does-it-leave-with-the-person
c5313ab2c756762d56257c9da0ece9ada86a55d5fb6b0181d4f80b52617d27af  2026-09-08  the-thing-you-didnt-know-to-look
e2c8af2a883e85288a4d7cb1e5e79871727a80f6b4caf173f19b6cd426409ad1  2026-10-03  the-wager-settled
b23915c70030b8af3f0870924a3ea4a826d7c49a09744a8c9d55783b8691d4bf  2026-09-08  the-week-the-watch-went-dark
12fc0bda658f992c5981aca0ee21eee6ac167b6a4d8e0496a625b0b2d50cd9b0  2026-09-08  three-things-you-change-and-one-you
884f74f37fa85bafad4974dadcd02cbc482cb0d987d7fd047cbbb8e1e5bb8092  2026-09-08  welcome-to-office-hours
96af90c214eeb3496a7e05806eed3ae22f89db569254b50b06e238e76d42ecfa  2026-09-08  what-an-mcp-actually-is-without-the
ada015eb98a1704c351df089fcba34dc6a5ad94c8f080a855dd67e7f70c88d0c  2026-09-08  what-fifteen-years-teaches-that-no
2abc5f6979c5c4ffa4625e3638ec618170b642cd5cb5d154cd526e71e1961e51  2026-09-08  what-four-hundred-dollars-actually
```

## `_md/*.md`

```
315f8533725c117490e15d7022bddbe510671f9a16b2d090a6000c107e1150b8  2026-09-29  default-on-is-not-consent-substack
8658b71e0812cf101db735e1633a2b0b6d1485a8b51fed6ff232d2a4882aef55  2026-09-29  default-on-is-not-consent
09d475fd4d02844db692511daabc14474a4c75ee185fc1f16c053e97d2a194de  2026-09-08  even-the-guy-driving-your-uber-can
1e41a18d23a57f64303bb924cdafa9231f7433fa79113173765f291af9bd9be3  2026-09-08  executive-protection
d5fd6f3b35b23241f13ed7db96e8c9829e87bb335775219ce64267b93ce4fdc4  2026-10-20  five-tiers-one-account
19def1ee2d26e95715a111fbb3b510fbe543a0d1a38a3f7290569ccab2f9c021  2026-09-08  i-drove-through-surge-for-a-year
400298510a0b3e3a2884580bd38e94a6b9cb12ce8290703e00830081c4c26cde  2026-09-08  index
34d7f30fca94fdf9c809e421d87614e02ad70196fb0c7264cb73810387f3847a  2026-10-23  let-strangers-audit-you
f45c01612195c9c103f7aad1d3de11b77d3c6b28dfef3ac02ff95162cf5230fa  2026-10-21  living-inside-one-small-computer
09db1ed9c2d1c372e972ad2cd8aee243a757bb40a50dbbb94c323616b2be49d9  2026-09-08  only-the-writer-went-dark
06f2d6aeb3662598d00924972946d528462070078bcaf5ec04ea2f78b9fe5623  2026-09-15  own-your-dns-or-someone-else-will
cc1f63812715e2be4b115705d4dfe58832e0920f53915d3222e858220b81ec02  2026-10-24  right-model-right-task
3d40876322d626f78646d7dbde633663142307a487b3803bd292fa4c6ba332cb  2026-09-08  same-ride-same-minute-two-different
7bb33ff0094b4c1714736913e7a1300c3d9cf991b39557c1b415994d8d5d410f  2026-09-08  see-where-you-tap
6efd4a5b60f9b7e8c0a963352853912cfd43e430de740223dcc33585971a252c  2026-09-08  skills-are-not-systems
e8c40d585294fc925cf4d09480691cd7191e0b61cf61dea366b163455aa9938d  2026-09-08  teaser-own-your-dns
0aa24f6d39544e25dada7bbf4ecccfed51dc6c2214664e3bff16f268b1b354fa  2026-10-21  teaser-the-button-i-dont-get-to-press
60384bf93cf95dc4501d20a2a073bbae44436c757200a6e4191fe657f5acd6bc  2026-10-21  teaser-the-lock-that-didnt-care-i-was-right
94db76e2d82f0b9e5f0b8bf58c0637278d5da8c6189735e47ae2aaef750b7516  2026-09-08  the-access-no-one-bothered-to-earn
12c9f8cd1b058a582b1f627413dc727ca9e966090d6b6d95483a520fa53cec7a  2026-09-18  the-checkpoint-you-build-yourself
8be9fe9ff37060ec41aaae45e7bafcd1db90a6dd7795bec357aeb8328917d3f0  2026-09-08  the-four-hundred-dollar-experiment
4ea6d15a3da1a40077b2741d8d695ef4be30855cef8060671150d0e2cdf062f0  2026-09-08  the-house-always-publishes-its-odds
196c4ff738ada9e06aef29f1a11195c970f95c53b6c907d54e91d282a532c60d  2026-09-29  the-landing-that-never-happened-substack
351a6d162b8518bdd0109799e6164c2334be5d81cfd6783406b2a7210e552d3b  2026-09-29  the-landing-that-never-happened
2e707e62ccffc74b7f7b8b9e79a44ee99fa002acb13b91857ef6d11c15080278  2026-09-08  the-machine-in-the-closet
014a0fa96423c6f7528d5d587ed20e845fd2e3a26fc536ce89667e52a3571f90  2026-09-25  the-new-hire-you-dont-hand-the-keys
6678b875cc3108ed413943480fb56179b6540c65d819954b861a57a0a36bcba5  2026-09-09  the-quiet-perimeter-tscm-digital-opsec
99301347bf961abfa812356f7b8cf34def792e341a0c3711464d77563f7c6f9f  2026-09-08  the-squeeze-isnt-the-goal-its-the
6bba4d0a98bccb0eec96502ba8c6b1e70208830fb733621c4db9f53ab13fa851  2026-10-19  the-switch-they-dont-need
27bb7f826f7df013e0b0a19be58aaf25957f1e5551cf615bcf7abe25eb370178  2026-09-08  the-tell-does-it-leave-with-the-person
3b805b3d76862e6c955fbb512cf568aef7b5575a7cf2684392317e9826d9217a  2026-10-22  the-terminal-that-doesnt-stop-the-radio
42342875b9d70be0dcdf0556c2f53c38ed6f27aac824d3619865363da41c10f6  2026-09-08  the-thing-you-didnt-know-to-look
358c3f303521176fbdce4ac1a83071d0d18c78da5b4e34e986296e8c32ceb91e  2026-09-08  the-wager-settled
6c21d5f445c8a9a730a0ebe4ca72de6f55559687c0fafc1c25d5786ab7885d21  2026-09-08  the-week-the-watch-went-dark
d4434c17a9c4674bc2b7018b05ec1f640957103682600b6935f1dc1ce3634a54  2026-10-14  three-agents-one-signature
4de90766fe0efdbb86dc0e4d802acf8267cd4d8b5a248c4003197aa5248b9122  2026-09-08  three-things-you-change-and-one-you
5035aaf332111d387b895d42fe373165c9955cb7c84cc67175e6981056962d1c  2026-10-16  three-weeks-to-v1
3cfe7fe5ae343948497614a40f8adb278ac1ed6bd575a73619e724fb1e23c4fb  2026-09-08  welcome-to-office-hours
c762b2e44ae2caeb8128eb72690afbd60026dbbbf7265915a8f759ec73306fd6  2026-09-08  what-an-mcp-actually-is-without-the
8b9ced3aebf4f5fe8b7e005d8c0395f1dba2b2c70aad772325e7f1f8f430cb0e  2026-09-08  what-fifteen-years-teaches-that-no
36375218b2d80fbffddfe16865456a61e4331e3a237d70723d3535a69f7b382d  2026-09-08  what-four-hundred-dollars-actually
```
