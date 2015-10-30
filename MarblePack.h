#ifndef MARBLEPACK_H
#define MARBLEPACK_H



#include <map>


namespace MarblePack
{

	template <typename PpmModelConfig_>
	class PpmModelBuilder
	{
	public:
		typedef typename PpmModelConfig_::Symbol      Symbol;
		typedef typename PpmModelConfig_::SymbolCount SymbolCount;

		class PpmContextBuilder
		{
			typedef std::map<Symbol, SymbolCount> Symbols;

		private:
			Symbols _symbols;

		public:
			PpmContextBuilder()
			{ }

			void AddSymbol(Symbol symbol, SymbolCount count)
			{
				std::pair<typename Symbols::iterator, bool> it = _symbols.insert(std::make_pair(symbol, count));
				if (!it.second)
					it.first->second += count;
			}

			SymbolCount GetTotalCount() const
			{
				SymbolCount result = 0;
				for (typename Symbols::const_iterator it = _symbols.begin(); it != _symbols.end(); ++it)
					result += it->second;
				return result;
			}
		};

	private:
		static const size_t ContextSize = PpmModelConfig_::ContextSize;
		typedef std::map<std::array<Symbol, ContextSize>, PpmContextBuilder> Contexts;

	private:
		PpmModelConfig_ _config;

	public:
		PpmModelBuilder(PpmModelConfig_ config = PpmModelConfig_()) : _config(config)
		{ }

		void AddSymbol(const std::array<Symbol, ContextSize>& context, Symbol symbol, SymbolCount count)
		{ _contexts[context].AddSymbol(symbol, count); }
	};


	namespace Detail
	{
		template <typename... PpmModelConfig_>
		struct ModelSortChecker;

		template <typename T>
		struct ModelSortChecker<T> : std::true_type
		{ };

		template <typename T1, typename T2, typename... Rest_>
		struct ModelSortChecker<T1, T2, Rest_...> :
			std::boolean_constant<T1::ContextSize < T2::ContextSize && ModelSortChecker<T2, Rest_...>>
		{ };


		template <typename... PpmModelConfig_>
		struct LastParam;

		template <typename T>
		struct LastParam<T>
		{ typedef T Type; };

		template <typename T, typename... Tail_>
		struct LastParam<T, Tail_...>
		{ typedef typename LastParam<Tail_...>::Type Type; }
	};


	template <typename... PpmModelConfig_>
	class PpmPredictorBuilder
	{
		typedef std::tuple<PpmModelBuilder<PpmModelConfig_>...> ModelBuilders;
		typedef LastParam<PpmModelConfig_>::Type LastModel;

		static constexpr size_t LastModel::ContextSize = MaxContextSize;

	private:
		ModelBuilders                      _models;
		std::array<Symbol, MaxContextSize> _context;

	public:
		PpmPredictorBuilder()
		{ static_assert(Detail::ModelSortChecker<PpmModelConfig_...>, "Model configs must be sorted ascending order!"); }

		void Update(Symbol symbol)
		{ _contexts[context].AddSymbol(symbol, count); }
	};

}

#endif
