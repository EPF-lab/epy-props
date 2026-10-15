# Posición principal / alterna (criterio propio, estilo DvP de 5 posiciones). Confianza "manual".
RAW = """
tyrese maxey:PG/SG; amen thompson:SG/SF; kevin durant:PF/SF; luka doncic:PG; trey murphy iii:SF/SG; jamal murray:PG
james harden:PG/SG; jalen johnson:PF/SF; jabari smith jr.:PF; vj edgecombe:SG; jalen brunson:PG; anthony edwards:SG
nikola jokic:C; paolo banchero:PF; austin reaves:SG/PG; keegan murray:PF/SF; lauri markkanen:PF/C; jaylen brown:SF/SG
derrick white:SG/PG; cade cunningham:PG; brandon ingram:SF; desmond bane:SG; scottie barnes:PF/SF; cooper flagg:SF/PF
devin booker:SG; donovan mitchell:SG; nickeil alexander-walker:SG/PG; alperen sengun:C; toumani camara:SF/PF; deni avdija:SF/PF
pascal siakam:PF; og anunoby:SF/PF; shai gilgeous-alexander:PG; dyson daniels:SG/SF; kevin porter jr.:PG; lebron james:SF/PF
keyonte george:PG; julius randle:PF; mikal bridges:SF; jayson tatum:SF/PF; michael porter jr.:SF/PF; payton pritchard:PG/SG
bam adebayo:C; kennedy chandler:PG; josh giddey:PG; ryan rollins:PG; kawhi leonard:SF; immanuel quickley:PG
evan mobley:PF/C; christian braun:SG/SF; bennedict mathurin:SG/SF; jaden mcdaniels:PF/SF; joel embiid:C; kon knueppel:SG/SF
kelly oubre jr.:SF; zach lavine:SG; anthony davis:C/PF; andrew nembhard:PG; tyler herro:SG; rudy gobert:C
saddiq bey:SF/PF; demar derozan:SF/SG; jimmy butler:SF; karl-anthony towns:C/PF; de'aaron fox:PG; miles bridges:PF/SF
p.j. washington:PF; onyeka okongwu:C; julian reese:C; ivica zubac:C; rayan rupert:SF; stephen curry:PG
cj mccollum:SG/PG; nikola vucevic:C; walker kessler:C; paul george:SF/PF; jaren jackson jr.:PF/C; devin vassell:SG/SF
dariq whitehead:SF/SG; cameron johnson:SF/PF; darius garland:PG; donte divincenzo:SG; dillon brooks:SF; andrew wiggins:SF
rj barrett:SF/SG; brandon miller:SF; josh hart:SG/SF; stephon castle:PG/SG; franz wagner:SF; anthony black:PG/SG
aaron nesmith:SF; domantas sabonis:C/PF; zion williamson:PF; jerami grant:PF/SF; peyton watson:SF/PF; norman powell:SG
naji marshall:SF/PF; shaedon sharpe:SG; jrue holiday:PG; quentin grimes:SG; wendell carter jr.:C; matas buzelis:PF/SF
victor wembanyama:C; coby white:PG; a.j. green:SG; max christie:SG; russell westbrook:PG; kyshawn george:SF
leaky black:SF; giannis antetokounmpo:PF; chet holmgren:C/PF; ayo dosunmu:SG/PG; jaden ivey:SG/PG; grayson allen:SG
davion mitchell:PG; collin gillespie:PG; ja morant:PG; brandin podziemski:SG/PG; marcus smart:PG/SG; jalen williams:SF/SG
royce o'neale:SF; herbert jones:SF; rui hachimura:PF; jaime jaquez jr.:SF/SG; anfernee simons:SG; jalen duren:C
lamelo ball:PG; trae young:PG; santi aldama:PF/C; aaron gordon:PF; dejounte murray:PG; nic claxton:C
tobias harris:PF; bub carrington:PG; ace bailey:SF; jalen suggs:SG/PG; julian champagnie:SF; draymond green:PF/C
duncan robinson:SF/SG; kris dunn:PG; deandre ayton:C; alex sarr:C/PF; donovan clingan:C; john collins:PF
jarrett allen:C; tre jones:PG; noah clowney:PF; derrick jones jr.:SF/PF; myles turner:C; jaylon tyson:SF/SG
isaac okoro:SF; ousmane dieng:SF/PF; luguentz dort:SG; cason wallace:SG/PG; tim hardaway jr.:SG; sam merrill:SG
maxime raynaud:C; jusuf nurkic:C; jaylen wells:SF; dennis schroder:PG; pelle larsson:SG; miles mcbride:PG
john konchar:SG; kyle kuzma:PF; reed sheppard:PG/SG; de'andre hunter:SF; bilal coulibaly:SF; naz reid:C/PF
keshon gilbert:PG; moussa diabate:C; collin sexton:SG/PG; ausar thompson:SF; jalen green:SG; tari eason:PF/SF
ajay mitchell:SG/PG; harrison barnes:PF/SF; zach edey:C; jeremiah fears:PG; cedric coward:SF; isaiah collier:PG
moses moody:SG/SF; jarace walker:PF; neemias queta:C; egor demin:PG/SG; nique clifford:SG/SF; jake laravia:PF/SF
walter clayton:PG/SG; jakob poeltl:C; derik queen:C; scoot henderson:PG; sam hauser:SF/PF; keon ellis:SG
tristan da silva:SF/PF; kobe brown:PF/SF; guerschon yabusele:PF; cormac ryan:SG; lawson lovering:C; bruce brown:SG/SF
cody williams:SF; khris middleton:SF; terance mann:SG/SF; cam thomas:SG; kristaps porzingis:C/PF; bobby portis:PF/C
isaiah hartenstein:C; taylor hendricks:PF; tre johnson:SG; jordan poole:SG/PG; precious achiuwa:PF/C; dominick barlow:PF
cam spencer:SG; jonathan kuminga:PF/SF; jock landale:C; mark williams:C; kevin huerter:SG/SF; brice sensabaugh:SF
taurean prince:SF; kyle filipowski:C/PF; kris murray:PF/SF; keldon johnson:SF; svi mykhailiuk:SF/SG; leonard miller:PF/SF
luke kennard:SG; landry shamet:SG; de'anthony melton:SG/PG; ziaire williams:SF; steven adams:C; isaiah stewart:C/PF
ty jerome:PG/SG; dylan harper:PG/SG; jamal shead:PG; sion james:SG/SF; jordan goodwin:SG/PG; mouhamadou gueye:PF
nick richards:C; zaccharie risacher:SF; kyle anderson:PF/SF; dean wade:PF; vit krejci:SG/PG; nolan traore:PG
brandon williams:PG; spencer jones:SF; kel'el ware:C; will riley:SF; jordan miller:SF; oso ighodaro:C/PF
malik monk:SG/PG; sandro mamukelashvili:PF/C; collin murray-boyles:PF; jose alvarado:PG; brook lopez:C; aaron wiggins:SG/SF
daniel gafford:C; klay thompson:SG/SF; vince williams jr.:SG/SF; al horford:C/PF; rob dillingham:PG; marvin bagley iii:PF/C
ryan kalkbrenner:C; ben sheppard:SG/SF; gg jackson ii:PF; kentavious caldwell-pope:SG; scotty pippen jr.:PG; isaiah joe:SG
gary trent jr.:SG; jay huff:C; bryce mcgowens:SG; drake powell:SF; luke kornet:C; ben saraf:PG; lonzo ball:PG
danny wolf:C/PF; jalen smith:C/PF; caleb love:SG; jamir watkins:SF; dylan cardwell:C; ja'kobe walter:SG; gui santos:SF
patrick williams:PF; jaden hardy:SG; blake hinson:SF; jevon carter:PG; javon small:PG; bradley beal:SG; daniss jenkins:PG
justin champagnie:SF; daquan jeffries:SF/SG; charles bassey:C; will richard:SG; kobe sanders:SG; ron holland:SF; grant williams:PF
jericho sims:C; yves missi:C; bogdan bogdanovic:SG; mitchell robinson:C; jaylin williams:C/PF; andre drummond:C
ryan nembhard:PG; john poulakidas:SG; corey kispert:SF; ryan dunn:SF/PF; gabe vincent:PG; micah potter:PF/C; josh minott:PF
caris levert:SG; sidy cissoko:SF; d'angelo russell:PG; mo bamba:C; tyrese martin:SF; day'ron sharpe:C
olivier-maxence prosper:SF/PF; pat spencer:PG; baylor scheierman:SF; johnny furphy:SF; zach collins:C/PF; devin carter:PG
mike conley:PG; quenton jackson:SG; jaxson hayes:C; alex caruso:SG; jared mccain:SG/PG; craig porter jr.:PG
jordan clarkson:SG/PG; jordan walsh:SF; kasparas jakucionis:PG/SG; obi toppin:PF; killian hayes:PG; javonte green:SF
jeremiah robinson-earl:PF; buddy hield:SG; nicolas batum:PF/SF; josh okogie:SG/SF; jarred vanderbilt:PF; adem bona:C
anthony gill:PF; quinten post:C; nikola jovic:PF/SF; t.j. mcconnell:PG; robert williams:C; sharife cooper:PG
cameron payne:PG; cam whitmore:SF; dorian finney-smith:PF; isaiah jackson:C; simone fontecchio:SF; kam jones:SG
oscar tshiebwe:C; tyus jones:PG; kevin love:C/PF; deandre jordan:C; bones hyland:PG; dereck lively ii:C
dru smith:SG/PG; trendon watford:PF; luka garza:C; lj cryer:SG; ochai agbaji:SF/SG; jalen pickett:PG
matisse thybulle:SF/SG; nikola topic:PG; kj simpson:PG; jalen wilson:SF/PF; payton sandfort:SF; tyson etienne:SG
josh green:SG/SF; nae'qwan tomlin:PF; pete nance:PF; gary payton ii:SG/PG; pj hall:C; tidjane salaun:PF/SF
kenrich williams:PF/SF; justin edwards:SF; mouhamed gueye:PF; goga bitadze:C; doug mcdermott:SF; julian strawther:SF/SG
cole anthony:PG; micah peavy:SF; josh oduro:PF; max strus:SF/SG
"""
def parse():
    out={}
    for item in RAW.replace("\n",";").split(";"):
        item=item.strip()
        if not item: continue
        name,pos=item.rsplit(":",1)
        p=pos.split("/")
        out[name.strip()]=(p[0], p[1] if len(p)>1 else "")
    return out
