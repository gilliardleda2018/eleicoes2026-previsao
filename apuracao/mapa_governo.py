"""Mapa factual da liderança entre os dois candidatos acompanhados."""
import numpy as np
import plotly.express as px

def figura(d, geo, ensaio=False):
    mapa = d.copy()
    mapa['lideranca'] = np.select(
        [mapa.contado_vv <= 0, mapa.contado_a > mapa.contado_b, mapa.contado_b > mapa.contado_a],
        ['Sem votos', 'Braide', 'Orleans'], default='Empate')
    fig = px.choropleth_map(
        mapa, geojson=geo, locations='cd_ibge', featureidkey='properties.CD_MUN',
        color='lideranca', color_discrete_map={'Braide':'#1F6FB2','Orleans':'#E07B1F',
        'Empate':'#B8BDC5','Sem votos':'#E2E5E9'},
        category_orders={'lideranca':['Braide','Orleans','Empate','Sem votos']},
        map_style='carto-positron', zoom=5.3, center={'lat':-5.2,'lon':-45.2},
        opacity=.85, height=560, hover_name='municipio',
        hover_data={'cd_ibge':False,'contado_a':':,.0f','contado_b':':,.0f','pst':':.1f'},
        labels={'lideranca':'Liderança no recorte','contado_a':'Votos de Braide',
                'contado_b':'Votos de Orleans','pst':'Seções apuradas (%)'},
        title='Votação por município' + (' · ENSAIO' if ensaio else ' · votos apurados'))
    fig.update_layout(margin=dict(t=50,b=0,l=0,r=0),legend=dict(orientation='h'))
    return fig
